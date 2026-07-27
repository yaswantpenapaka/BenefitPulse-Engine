"""Context-aware Assistant Agent with RAG-grounded answers."""

from __future__ import annotations

import logging
from typing import Any, Optional

from app.config import get_settings
from app.rag.vector_store import get_vector_store

logger = logging.getLogger(__name__)


def run_assistant(
    message: str,
    claim_context: Optional[dict] = None,
    benefit_context: Optional[dict] = None,
    conversation_history: Optional[list[dict[str, str]]] = None,
) -> dict[str, Any]:
    """
    Answer user questions about claims / benefits using RAG + optional Gemini.
    Always tries to cite policy sources.
    """
    store = get_vector_store()

    context_bits: list[str] = []
    if benefit_context:
        context_bits.append(
            f"Detected benefit: {benefit_context.get('benefit_type')} | "
            f"confidence: {benefit_context.get('confidence_score')} | "
            f"status: {benefit_context.get('status')} | "
            f"merchant: {benefit_context.get('merchant')} | "
            f"amount: {benefit_context.get('amount')} | "
            f"explanation: {benefit_context.get('explanation')} | "
            f"policy: {benefit_context.get('policy_reference')}"
        )
    if claim_context:
        pref = claim_context.get("prefilled_data") or {}
        context_bits.append(
            f"Claim status: {claim_context.get('status')} | "
            f"missing docs: {claim_context.get('missing_documents')} | "
            f"prefilled: benefit={pref.get('benefit_type')}, "
            f"merchant={pref.get('merchant')}, amount={pref.get('amount')}, "
            f"remaining days={pref.get('coverage_remaining_days')}"
        )

    context_str = "\n".join(context_bits) if context_bits else "No specific claim selected."

    chunks = store.query(message, top_k=4)
    policy_text = "\n\n---\n\n".join(
        f"Source: {c['source']}\n{c['text']}" for c in chunks
    )
    citations = list({c["source"] for c in chunks})
    sources = [
        {"source": c["source"], "title": c["title"], "score": c.get("score", 0)}
        for c in chunks
    ]

    settings = get_settings()
    reply: Optional[str] = None

    if settings.has_gemini:
        try:
            import google.generativeai as genai

            genai.configure(api_key=settings.google_api_key)
            history_txt = ""
            if conversation_history:
                for m in conversation_history[-6:]:
                    role = m.get("role", "user")
                    history_txt += f"{role}: {m.get('content', '')}\n"

            prompt = f"""You are the BenefitPulse assistant — friendly, precise, and practical.
Answer using ONLY the policy context and claim context below.
Cite policy document names when you talk about coverage.
If something is unclear, say what you know and what docs would help.
Keep it short (2–5 short paragraphs or bullets). Sound human, not corporate.

CLAIM / BENEFIT CONTEXT:
{context_str}

POLICY CONTEXT:
{policy_text}

CONVERSATION:
{history_txt}

USER QUESTION:
{message}

Respond in plain text (no JSON). Include a short "Sources:" line at the end listing policy file names used.
"""
            last_err: Optional[Exception] = None
            for model_name in settings.gemini_model_candidates:
                try:
                    model = genai.GenerativeModel(model_name)
                    resp = model.generate_content(prompt)
                    reply = (resp.text or "").strip()
                    if reply:
                        break
                except Exception as e:
                    last_err = e
                    logger.warning("Assistant model %s failed: %s", model_name, e)
            if not reply and last_err:
                logger.warning("Assistant LLM failed on all models: %s", last_err)
        except Exception as e:
            logger.warning("Assistant LLM failed: %s", e)

    if not reply:
        reply = _fallback_reply(message, context_str, chunks, benefit_context, claim_context)

    return {
        "reply": reply,
        "citations": citations,
        "sources": sources,
    }


def _fallback_reply(
    message: str,
    context_str: str,
    chunks: list[dict],
    benefit_context: Optional[dict],
    claim_context: Optional[dict],
) -> str:
    msg = message.lower()
    lines: list[str] = []

    if benefit_context:
        lines.append(
            f"**Your detected benefit:** {benefit_context.get('benefit_type')} "
            f"(confidence {int(float(benefit_context.get('confidence_score') or 0) * 100)}%)."
        )
        if benefit_context.get("explanation"):
            lines.append(benefit_context["explanation"])

    if any(k in msg for k in ("eligible", "why", "qualify", "coverage")):
        if chunks:
            snippet = chunks[0]["text"][:500]
            lines.append(f"According to **{chunks[0]['title']}**:\n{snippet}")
        elif benefit_context:
            lines.append(
                f"Policy reference: {benefit_context.get('policy_reference', 'See benefit guides')}."
            )
        else:
            lines.append(
                "Eligible items purchased with The Platinum Card® or the American Express® Gold Card may qualify "
                "for Purchase Protection (90 days), Return Protection, Travel Delay Insurance, "
                "or Extended Warranty depending on category."
            )

    elif any(k in msg for k in ("document", "receipt", "upload", "need", "required")):
        missing = []
        if claim_context:
            missing = claim_context.get("missing_documents") or []
        if missing:
            lines.append("Still needed for this claim: " + ", ".join(missing) + ".")
        lines.append(
            "Typically you need: proof of purchase (receipt/invoice), Card statement showing the charge, "
            "and for damage/theft claims — photos and/or a police report."
        )
        if chunks:
            lines.append(f"See also: {chunks[0]['source']}")

    elif any(k in msg for k in ("exclude", "not covered", "ineligible")):
        lines.append(
            "Common exclusions include consumables (food, fuel), motor vehicles, cash, "
            "digital goods, commercial resale inventory, and normal wear and tear."
        )
        for c in chunks:
            if "exclu" in c["source"].lower() or "exclu" in c["text"].lower():
                lines.append(c["text"][:400])
                break

    elif any(k in msg for k in ("deadline", "window", "days", "expire")):
        if claim_context and claim_context.get("prefilled_data"):
            pref = claim_context["prefilled_data"]
            lines.append(
                f"Coverage window: {pref.get('coverage_window_days')} days. "
                f"Remaining: {pref.get('coverage_remaining_days')} days. "
                f"Claim deadline: {pref.get('claim_deadline', 'see policy')}."
            )
        else:
            lines.append(
                "Purchase Protection and Return Protection generally cover 90 days from purchase. "
                "Travel Delay claims should be filed promptly (often within 30 days of the delay)."
            )

    else:
        lines.append(
            "I can help with eligibility, required documents, coverage windows, and exclusions "
            "for Purchase Protection, Return Protection, Travel Delay, and Extended Warranty."
        )
        if benefit_context:
            lines.append(
                f"You currently have a **{benefit_context.get('benefit_type')}** detection open. "
                "Ask me why you're eligible or what to upload next."
            )
        if chunks:
            lines.append(f"Relevant policy excerpt from **{chunks[0]['title']}**:\n{chunks[0]['text'][:350]}…")

    sources = list({c["source"] for c in chunks})
    if sources:
        lines.append("\nSources: " + ", ".join(sources))

    return "\n\n".join(lines)
