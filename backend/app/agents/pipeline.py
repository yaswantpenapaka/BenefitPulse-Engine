"""
LangGraph multi-agent pipeline for benefit detection.

Pipeline:
  Transaction Intelligence → Benefit Knowledge (RAG) → Rules Engine
  → Confidence Agent → (conditional) Claim Prefill → END
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any, Literal, Optional, TypedDict

from app.config import get_settings
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)

# Tracks whether Gemini LLM calls succeeded during a pipeline run (for demo UI).
_llm_stats: dict[str, int] = {"attempted": 0, "succeeded": 0}


class BenefitActivationState(TypedDict, total=False):
    transaction: dict
    user_id: str
    card_id: str
    card_tier: str
    transaction_intelligence: Optional[dict]
    retrieved_policy_chunks: Optional[list]
    benefit_candidates: Optional[list]
    rules_decision: Optional[dict]
    confidence_score: Optional[float]
    confidence_breakdown: Optional[dict]
    prefilled_claim: Optional[dict]
    missing_documents: Optional[list]
    explanation: Optional[str]
    current_step: str
    status: str
    error: Optional[str]


# ── Merchant / category heuristics (fallback when LLM unavailable) ────

MERCHANT_MAP = {
    r"amzn|amazon": ("Amazon", "Electronics"),
    r"apple\.com|apple store": ("Apple", "Electronics"),
    r"flipkart": ("Flipkart", "Electronics"),
    r"croma": ("Croma", "Electronics"),
    r"reliance digital": ("Reliance Digital", "Electronics"),
    r"indigo|6e-|air india|spicejet|vistara": ("Airline", "Travel"),
    r"makemytrip|goibibo|booking\.com|expedia": ("Travel Agency", "Travel"),
    r"swiggy|zomato|dominos|mcdonald": ("Food Delivery", "Food & Dining"),
    r"indian oil|bpcl|hpcl|shell|petrol|fuel": ("Fuel Station", "Fuel"),
    r"myntra|ajio|zara|h&m|uniqlo": ("Apparel Retailer", "Apparel"),
    r"ikea|hometown|urban ladder": ("Furniture", "Home"),
    r"uber|ola cabs": ("Ride Share", "Transport"),
}

ELIGIBLE_CATEGORIES = {
    "Purchase Protection": {"Electronics", "Home", "Apparel", "Furniture"},
    "Return Protection": {"Apparel", "Electronics", "Home"},
    "Travel Delay Insurance": {"Travel"},
    "Extended Warranty": {"Electronics", "Home"},
}

EXCLUDED_CATEGORIES = {"Food & Dining", "Fuel", "Transport"}


def _llm_json(prompt: str) -> Optional[dict]:
    settings = get_settings()
    if not settings.has_gemini:
        return None
    _llm_stats["attempted"] += 1
    try:
        import google.generativeai as genai

        genai.configure(api_key=settings.google_api_key)
        last_err: Optional[Exception] = None
        for model_name in settings.gemini_model_candidates:
            try:
                model = genai.GenerativeModel(
                    model_name,
                    generation_config={
                        "response_mime_type": "application/json",
                        "temperature": 0.1,
                    },
                )
                resp = model.generate_content(prompt)
                text = (resp.text or "{}").strip()
                # Tolerate markdown fences if the model wraps JSON
                if text.startswith("```"):
                    text = re.sub(r"^```(?:json)?\s*", "", text)
                    text = re.sub(r"\s*```$", "", text)
                parsed = json.loads(text)
                _llm_stats["succeeded"] += 1
                if model_name != settings.gemini_model:
                    logger.info("LLM succeeded with fallback model %s", model_name)
                return parsed
            except Exception as e:
                last_err = e
                logger.warning("LLM model %s failed: %s", model_name, e)
                continue
        if last_err:
            logger.warning("All LLM models failed; last error: %s", last_err)
        return None
    except Exception as e:
        logger.warning("LLM call failed: %s", e)
        return None


# ── Agent Nodes ───────────────────────────────────────────────────────

def transaction_intelligence_node(state: BenefitActivationState) -> dict:
    """Normalize merchant, classify category and product type."""
    txn = state.get("transaction") or {}
    raw = (txn.get("merchant_raw") or "").strip()
    amount = float(txn.get("amount") or 0)
    existing_cat = txn.get("category")
    existing_norm = txn.get("merchant_normalized")
    description = txn.get("description") or ""

    llm_result = _llm_json(
        f"""You are a transaction intelligence agent for credit card benefits.
Normalize this merchant descriptor and classify the purchase.
Return JSON with keys: merchant_normalized, category, product_type, confidence (0-1).
Categories: Electronics, Travel, Apparel, Food & Dining, Fuel, Home, Transport, Other.

merchant_raw: {raw}
description: {description}
amount: {amount}
mcc: {txn.get('mcc')}
"""
    )

    if llm_result:
        intel = {
            "merchant_normalized": llm_result.get("merchant_normalized") or existing_norm or raw,
            "category": llm_result.get("category") or existing_cat or "Other",
            "product_type": llm_result.get("product_type") or description or "Unknown",
            "confidence": float(llm_result.get("confidence") or 0.8),
        }
    else:
        merchant = existing_norm or raw
        category = existing_cat or "Other"
        conf = 0.75
        raw_l = raw.lower()
        for pattern, (m_name, cat) in MERCHANT_MAP.items():
            if re.search(pattern, raw_l):
                merchant = existing_norm or m_name
                category = existing_cat or cat
                conf = 0.92
                break
        product = description or category
        # Infer product from description keywords
        desc_l = description.lower()
        if any(k in desc_l for k in ("laptop", "macbook", "iphone", "phone", "tv", "headphone")):
            category = existing_cat or "Electronics"
            conf = max(conf, 0.9)
        intel = {
            "merchant_normalized": merchant,
            "category": category,
            "product_type": product,
            "confidence": conf,
        }

    return {
        "transaction_intelligence": intel,
        "current_step": "transaction_intelligence",
        "status": "processing",
    }


def benefit_knowledge_node(state: BenefitActivationState) -> dict:
    """RAG retrieval of relevant policy chunks + candidate benefits."""
    intel = state.get("transaction_intelligence") or {}
    category = intel.get("category", "Other")
    merchant = intel.get("merchant_normalized", "")
    product = intel.get("product_type", "")

    query = (
        f"Eligible benefits for {category} purchase of {product} from {merchant}. "
        f"Purchase protection return protection travel delay extended warranty exclusions."
    )
    store = get_vector_store()
    chunks = store.query(query, top_k=5)

    candidates: list[dict] = []
    if category in ELIGIBLE_CATEGORIES["Purchase Protection"]:
        candidates.append(
            {
                "benefit_type": "Purchase Protection",
                "reason": f"{category} items may qualify for 90-day accidental damage/theft coverage",
            }
        )
    if category in ELIGIBLE_CATEGORIES["Return Protection"]:
        candidates.append(
            {
                "benefit_type": "Return Protection",
                "reason": f"{category} may qualify if merchant return policy is restrictive",
            }
        )
    if category in ELIGIBLE_CATEGORIES["Travel Delay Insurance"]:
        candidates.append(
            {
                "benefit_type": "Travel Delay Insurance",
                "reason": "Travel ticket charged to card may trigger delay expense coverage",
            }
        )
    if category in ELIGIBLE_CATEGORIES["Extended Warranty"]:
        candidates.append(
            {
                "benefit_type": "Extended Warranty",
                "reason": "Durable goods may receive extended manufacturer warranty",
            }
        )

    # Prefer Purchase Protection for electronics as primary
    if category == "Electronics" and candidates:
        candidates.sort(key=lambda c: 0 if c["benefit_type"] == "Purchase Protection" else 1)

    return {
        "retrieved_policy_chunks": chunks,
        "benefit_candidates": candidates,
        "current_step": "benefit_knowledge",
    }


def rules_evaluation_node(state: BenefitActivationState) -> dict:
    """Deterministic eligibility rules engine."""
    txn = state.get("transaction") or {}
    intel = state.get("transaction_intelligence") or {}
    candidates = state.get("benefit_candidates") or []
    card_tier = (state.get("card_tier") or "Platinum").title()
    category = intel.get("category", "Other")
    amount = float(txn.get("amount") or 0)

    # Parse transaction date
    txn_date_raw = txn.get("transaction_date")
    if isinstance(txn_date_raw, str):
        try:
            txn_date = datetime.fromisoformat(txn_date_raw.replace("Z", "+00:00"))
        except ValueError:
            txn_date = datetime.now(timezone.utc)
    elif isinstance(txn_date_raw, datetime):
        txn_date = txn_date_raw
    else:
        txn_date = datetime.now(timezone.utc)

    now = datetime.now(timezone.utc)
    if txn_date.tzinfo is None:
        txn_date = txn_date.replace(tzinfo=timezone.utc)
    days_since = (now - txn_date).days

    # Hard exclusions
    if category in EXCLUDED_CATEGORIES:
        return {
            "rules_decision": {
                "eligible": False,
                "benefit": None,
                "reasons": [f"Category '{category}' is excluded from protection benefits"],
                "window_remaining_days": 0,
                "max_coverage": 0,
            },
            "current_step": "rules_evaluation",
            "status": "not_eligible",
        }

    if not candidates:
        return {
            "rules_decision": {
                "eligible": False,
                "benefit": None,
                "reasons": ["No benefit candidates matched this transaction category"],
                "window_remaining_days": 0,
                "max_coverage": 0,
            },
            "current_step": "rules_evaluation",
            "status": "not_eligible",
        }

    # Evaluate primary candidate
    primary = candidates[0]
    benefit_type = primary["benefit_type"]

    window = 90
    max_coverage = 100000.0
    if benefit_type == "Travel Delay Insurance":
        window = 30
        max_coverage = 20000.0
    elif benefit_type == "Return Protection":
        window = 90
        max_coverage = 50000.0
    elif benefit_type == "Extended Warranty":
        window = 365
        max_coverage = 100000.0

    remaining = window - days_since
    reasons = []
    eligible = True

    eligible_tiers = {"Platinum", "Gold", "Centurion"}
    if card_tier not in eligible_tiers and card_tier != "Platinum":
        # Still allow for prototype demo cards
        reasons.append(f"Card tier {card_tier} – verifying eligibility")
    else:
        reasons.append(f"Card tier {card_tier} is eligible")

    if remaining < 0 and benefit_type != "Extended Warranty":
        eligible = False
        reasons.append(f"Coverage window of {window} days has expired ({days_since} days since purchase)")
    else:
        reasons.append(f"Within coverage window ({max(0, remaining)} days remaining of {window})")

    if amount <= 0:
        eligible = False
        reasons.append("Invalid transaction amount")
    elif amount > max_coverage:
        reasons.append(
            f"Amount ₹{amount:,.0f} exceeds per-occurrence limit ₹{max_coverage:,.0f}; claim capped"
        )
    else:
        reasons.append(f"Amount ₹{amount:,.0f} within coverage limit ₹{max_coverage:,.0f}")

    if category in ELIGIBLE_CATEGORIES.get(benefit_type, set()):
        reasons.append(f"Category '{category}' matches {benefit_type} eligible items")
    else:
        if benefit_type != "Travel Delay Insurance":
            eligible = False
            reasons.append(f"Category '{category}' does not match {benefit_type}")

    policy_ref = {
        "Purchase Protection": "Purchase Protection Guide – Section 3.2",
        "Return Protection": "Return Protection Policy – Section 2.1",
        "Travel Delay Insurance": "Travel Delay Insurance Certificate – Section 4.3",
        "Extended Warranty": "Extended Warranty Description of Coverage – Section 1.4",
    }.get(benefit_type, "Card Member Benefits")

    decision = {
        "eligible": eligible,
        "benefit": benefit_type if eligible else None,
        "reasons": reasons,
        "window_remaining_days": max(0, remaining),
        "coverage_window_days": window,
        "max_coverage": max_coverage,
        "policy_reference": policy_ref,
        "days_since_purchase": days_since,
    }

    return {
        "rules_decision": decision,
        "current_step": "rules_evaluation",
        "status": "eligible" if eligible else "not_eligible",
    }


def confidence_agent_node(state: BenefitActivationState) -> dict:
    """Compute composite confidence score and breakdown."""
    intel = state.get("transaction_intelligence") or {}
    rules = state.get("rules_decision") or {}
    chunks = state.get("retrieved_policy_chunks") or []

    merchant_conf = float(intel.get("confidence") or 0.7)
    category_conf = 0.9 if intel.get("category") not in (None, "Other") else 0.5
    rule_match = 0.95 if rules.get("eligible") else 0.2
    policy_match = 0.5
    if chunks:
        policy_match = min(0.95, 0.5 + max(c.get("score", 0) for c in chunks) * 0.5)
    receipt_status = 0.65  # not yet uploaded

    # Weighted composite
    score = (
        merchant_conf * 0.20
        + category_conf * 0.20
        + rule_match * 0.35
        + policy_match * 0.15
        + receipt_status * 0.10
    )
    score = round(min(0.99, max(0.05, score)), 2)

    breakdown = {
        "merchant_normalization": round(merchant_conf, 2),
        "category_match": round(category_conf, 2),
        "rule_match": round(rule_match, 2),
        "policy_match": round(policy_match, 2),
        "receipt_status": receipt_status,
    }

    return {
        "confidence_score": score,
        "confidence_breakdown": breakdown,
        "current_step": "confidence",
    }


def claim_prefill_node(state: BenefitActivationState) -> dict:
    """Generate near-complete pre-filled claim object + explanation."""
    txn = state.get("transaction") or {}
    intel = state.get("transaction_intelligence") or {}
    rules = state.get("rules_decision") or {}
    conf = state.get("confidence_score") or 0.0
    chunks = state.get("retrieved_policy_chunks") or []
    card_tier = state.get("card_tier") or "Platinum"

    benefit_type = rules.get("benefit") or "Purchase Protection"
    merchant = intel.get("merchant_normalized") or txn.get("merchant_raw")
    amount = float(txn.get("amount") or 0)
    max_cov = float(rules.get("max_coverage") or 100000)
    window = int(rules.get("coverage_window_days") or 90)
    remaining = int(rules.get("window_remaining_days") or 0)
    policy_ref = rules.get("policy_reference") or "Card Member Benefits"

    # Build explanation with policy citation
    citation = ""
    if chunks:
        citation = f" Grounded in: {chunks[0].get('title', 'policy')} ({chunks[0].get('source', '')})."

    explanation = (
        f"Your {merchant} purchase of {intel.get('product_type', 'item')} "
        f"({intel.get('category', 'item')}) is eligible under {benefit_type}. "
        f"{' '.join(rules.get('reasons', [])[:2])}. "
        f"Coverage: up to ₹{max_cov:,.0f}; {remaining} days remaining of {window}-day window. "
        f"Policy: {policy_ref}.{citation}"
    )

    # Optional LLM polish
    polished = _llm_json(
        f"""Rewrite this eligibility explanation for a cardholder in 2-3 clear sentences.
        Keep facts accurate. Return JSON: {{"explanation": "..."}}
        Facts: {explanation}
        """
    )
    if polished and polished.get("explanation"):
        explanation = polished["explanation"]

    missing = ["receipt_photo"]
    if benefit_type == "Travel Delay Insurance":
        missing = ["delay_certificate", "expense_receipts"]
    elif benefit_type == "Return Protection":
        missing = ["receipt_photo", "merchant_refusal"]
    elif benefit_type == "Purchase Protection":
        missing = ["receipt_photo"]  # police_report only if theft

    prefilled = {
        "benefit_type": benefit_type,
        "merchant": merchant,
        "merchant_raw": txn.get("merchant_raw"),
        "amount": amount,
        "currency": txn.get("currency", "INR"),
        "transaction_date": txn.get("transaction_date"),
        "transaction_id": txn.get("id"),
        "card_name": f"American Express {card_tier}",
        "card_type": card_tier,
        "category": intel.get("category"),
        "item_description": intel.get("product_type") or txn.get("description"),
        "coverage_window_days": window,
        "coverage_remaining_days": remaining,
        "max_coverage_amount": max_cov,
        "policy_reference": policy_ref,
        "explanation": explanation,
        "confidence_score": conf,
        "estimated_claim_amount": min(amount, max_cov),
        "incident_type": "accidental_damage_or_theft"
        if benefit_type == "Purchase Protection"
        else "other",
    }

    return {
        "prefilled_claim": prefilled,
        "missing_documents": missing,
        "explanation": explanation,
        "current_step": "claim_prefill",
        "status": "prefilled",
    }


def needs_review_node(state: BenefitActivationState) -> dict:
    return {
        "current_step": "needs_review",
        "status": "needs_review",
        "explanation": (
            "Confidence is below threshold for automatic pre-fill. "
            "A specialist review is recommended before claim submission."
        ),
    }


def route_after_confidence(state: BenefitActivationState) -> Literal["prefill", "prefill_review", "needs_review", "end_ineligible"]:
    rules = state.get("rules_decision") or {}
    conf = float(state.get("confidence_score") or 0)
    if not rules.get("eligible"):
        return "end_ineligible"
    if conf >= 0.85:
        return "prefill"
    if conf >= 0.60:
        return "prefill_review"
    return "needs_review"


def build_graph():
    """Compile LangGraph workflow. Falls back to sequential runner if import fails.

    Node names must NOT match state keys (LangGraph constraint).
    """
    try:
        from langgraph.graph import END, StateGraph

        graph = StateGraph(BenefitActivationState)
        # Node ids differ from state field names intentionally
        graph.add_node("node_txn_intel", transaction_intelligence_node)
        graph.add_node("node_benefit_rag", benefit_knowledge_node)
        graph.add_node("node_rules", rules_evaluation_node)
        graph.add_node("node_confidence", confidence_agent_node)
        graph.add_node("node_prefill", claim_prefill_node)
        graph.add_node("node_needs_review", needs_review_node)

        graph.set_entry_point("node_txn_intel")
        graph.add_edge("node_txn_intel", "node_benefit_rag")
        graph.add_edge("node_benefit_rag", "node_rules")
        graph.add_edge("node_rules", "node_confidence")
        graph.add_conditional_edges(
            "node_confidence",
            route_after_confidence,
            {
                "prefill": "node_prefill",
                "prefill_review": "node_prefill",
                "needs_review": "node_needs_review",
                "end_ineligible": END,
            },
        )
        graph.add_edge("node_prefill", END)
        graph.add_edge("node_needs_review", END)
        compiled = graph.compile()
        logger.info("LangGraph detection pipeline compiled successfully")
        return compiled
    except Exception as e:
        logger.warning("LangGraph compile failed, using sequential runner: %s", e)
        return None


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def run_detection_pipeline(
    transaction: dict,
    user_id: str = "",
    card_id: str = "",
    card_tier: str = "Platinum",
) -> BenefitActivationState:
    """Run the full multi-agent detection pipeline."""
    settings = get_settings()
    _llm_stats["attempted"] = 0
    _llm_stats["succeeded"] = 0

    initial: BenefitActivationState = {
        "transaction": transaction,
        "user_id": user_id,
        "card_id": card_id,
        "card_tier": card_tier,
        "current_step": "start",
        "status": "processing",
        "error": None,
    }

    result: BenefitActivationState
    graph = get_graph()
    if graph is not None:
        try:
            result = graph.invoke(initial)  # type: ignore
        except Exception as e:
            logger.exception("Graph invoke failed: %s", e)
            initial["error"] = str(e)
            result = _run_sequential(initial)
    else:
        result = _run_sequential(initial)

    # Attach runtime metadata for the live demo UI
    result["_mode"] = (  # type: ignore[typeddict-item]
        "gemini_live" if _llm_stats["succeeded"] > 0 else "rule_fallback"
    )
    result["_llm"] = {  # type: ignore[typeddict-item]
        "gemini_configured": settings.has_gemini,
        "gemini_model": settings.gemini_model if settings.has_gemini else None,
        "calls_attempted": _llm_stats["attempted"],
        "calls_succeeded": _llm_stats["succeeded"],
        "used_gemini": _llm_stats["succeeded"] > 0,
    }
    return result


def _run_sequential(initial: BenefitActivationState) -> BenefitActivationState:
    state: dict[str, Any] = dict(initial)
    for node in (
        transaction_intelligence_node,
        benefit_knowledge_node,
        rules_evaluation_node,
        confidence_agent_node,
    ):
        state.update(node(state))  # type: ignore

    route = route_after_confidence(state)  # type: ignore
    if route in ("prefill", "prefill_review"):
        state.update(claim_prefill_node(state))  # type: ignore
    elif route == "needs_review":
        state.update(needs_review_node(state))  # type: ignore

    return state  # type: ignore
