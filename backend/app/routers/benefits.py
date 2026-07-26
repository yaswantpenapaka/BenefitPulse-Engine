"""Detected benefits routes + detection pipeline trigger + transaction inject."""

from fastapi import APIRouter, Depends, HTTPException

from app.agents.pipeline import run_detection_pipeline
from app.models.schemas import DetectedBenefitDetail, DetectedBenefitOut, TransactionCreate
from app.services.auth import get_current_user_id
from app.services.store import get_store, persist_pipeline_audit

router = APIRouter(prefix="/benefits", tags=["benefits"])


def _pipeline_response(result: dict, *, transaction: dict | None = None, saved_benefit: dict | None = None) -> dict:
    rules = result.get("rules_decision") or {}
    return {
        "pipeline_status": result.get("status"),
        "eligible": bool(rules.get("eligible")),
        "confidence_score": result.get("confidence_score"),
        "confidence_breakdown": result.get("confidence_breakdown"),
        "transaction_intelligence": result.get("transaction_intelligence"),
        "rules_decision": rules,
        "benefit_candidates": result.get("benefit_candidates"),
        "prefilled_claim": result.get("prefilled_claim"),
        "missing_documents": result.get("missing_documents"),
        "explanation": result.get("explanation")
        or (
            "; ".join(rules.get("reasons") or [])
            if rules
            else None
        ),
        "policy_chunks": [
            {"source": c.get("source"), "title": c.get("title"), "score": c.get("score")}
            for c in (result.get("retrieved_policy_chunks") or [])
        ],
        "transaction": transaction,
        "saved_benefit": saved_benefit,
        "mode": result.get("_mode", "live_agents"),
        "llm": result.get("_llm"),
    }


@router.get("", response_model=list[DetectedBenefitOut])
def list_benefits(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    return [DetectedBenefitOut(**b) for b in store.get_benefits(user_id)]


@router.get("/{benefit_id}", response_model=DetectedBenefitDetail)
def get_benefit(benefit_id: str, user_id: str = Depends(get_current_user_id)):
    store = get_store()
    benefit = store.get_benefit(benefit_id, user_id)
    if not benefit:
        raise HTTPException(status_code=404, detail="Benefit not found")
    # Ensure claim draft exists
    store.ensure_claim_for_benefit(benefit_id, user_id)
    benefit = store.get_benefit(benefit_id, user_id)
    return DetectedBenefitDetail(**benefit)


@router.post("/detect/{transaction_id}")
def detect_for_transaction(
    transaction_id: str,
    user_id: str = Depends(get_current_user_id),
    persist: bool = True,
):
    """Run LangGraph detection pipeline on an existing transaction (live agents)."""
    store = get_store()
    txn = store.get_transaction(transaction_id)
    if not txn or txn.get("user_id") != user_id:
        raise HTTPException(status_code=404, detail="Transaction not found")

    cards = store.get_cards(user_id)
    card_tier = cards[0]["card_type"] if cards else "Platinum"
    card_id = txn.get("card_id") or (cards[0]["id"] if cards else "")

    result = run_detection_pipeline(
        transaction=txn,
        user_id=user_id,
        card_id=card_id,
        card_tier=card_tier,
    )
    persist_pipeline_audit(user_id, txn, result)

    saved = None
    if persist:
        saved = store.apply_pipeline_result(user_id, txn, result)

    return _pipeline_response(result, transaction=txn, saved_benefit=saved)


@router.post("/inject")
def inject_transaction_and_detect(
    body: TransactionCreate,
    user_id: str = Depends(get_current_user_id),
):
    """
    Inject a NEW transaction and (by default) run the full agent pipeline.

    Use this to verify agents are not hardcoded seed data.

    Examples that should become eligible:
    - Electronics laptop/phone purchase → Purchase Protection
    - Airline ticket → Travel Delay Insurance

    Examples that should be rejected:
    - Swiggy/Zomato food → excluded category
    - Petrol/fuel → excluded category
    """
    store = get_store()
    txn = store.add_transaction(
        user_id=user_id,
        merchant_raw=body.merchant_raw,
        amount=body.amount,
        description=body.description or "",
        category=body.category,
        mcc=body.mcc,
        currency=body.currency,
    )

    if not body.run_detection:
        return {
            "transaction": txn,
            "pipeline_status": "skipped",
            "message": "Transaction saved. Call POST /api/benefits/detect/{id} to run agents.",
        }

    cards = store.get_cards(user_id)
    card_tier = cards[0]["card_type"] if cards else "Platinum"
    result = run_detection_pipeline(
        transaction=txn,
        user_id=user_id,
        card_id=txn.get("card_id") or "",
        card_tier=card_tier,
    )
    persist_pipeline_audit(user_id, txn, result)
    saved = store.apply_pipeline_result(user_id, txn, result)
    return _pipeline_response(result, transaction=txn, saved_benefit=saved)
