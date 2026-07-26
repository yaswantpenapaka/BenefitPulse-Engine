"""Floating assistant chatbot endpoint."""

from fastapi import APIRouter, Depends, HTTPException

from app.agents.assistant import run_assistant
from app.models.schemas import AssistantRequest, AssistantResponse
from app.services.auth import get_current_user_id
from app.services.store import get_store

router = APIRouter(prefix="/assistant", tags=["assistant"])


@router.post("/chat", response_model=AssistantResponse)
def chat(body: AssistantRequest, user_id: str = Depends(get_current_user_id)):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message is required")

    store = get_store()
    claim_ctx = None
    benefit_ctx = None

    if body.claim_id:
        claim_ctx = store.get_claim(body.claim_id, user_id)
    if body.benefit_id:
        benefit_ctx = store.get_benefit(body.benefit_id, user_id)
        if benefit_ctx and not claim_ctx:
            claim_ctx = store.get_claim_by_benefit(body.benefit_id)

    result = run_assistant(
        message=body.message.strip(),
        claim_context=claim_ctx,
        benefit_context=benefit_ctx,
        conversation_history=body.conversation_history,
    )
    return AssistantResponse(**result)
