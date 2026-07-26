"""Claims review, update, submit, document upload."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.config import BASE_DIR
from app.models.schemas import ClaimOut, ClaimSubmitRequest, ClaimUpdateRequest
from app.services.auth import get_current_user_id
from app.services.store import get_store

router = APIRouter(prefix="/claims", tags=["claims"])

UPLOAD_DIR = BASE_DIR / "data" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.get("", response_model=list[ClaimOut])
def list_claims(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    return [ClaimOut(**c) for c in store.get_claims(user_id)]


@router.get("/{claim_id}", response_model=ClaimOut)
def get_claim(claim_id: str, user_id: str = Depends(get_current_user_id)):
    store = get_store()
    claim = store.get_claim(claim_id, user_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimOut(**claim)


@router.get("/by-benefit/{benefit_id}", response_model=ClaimOut)
def get_claim_by_benefit(benefit_id: str, user_id: str = Depends(get_current_user_id)):
    store = get_store()
    claim = store.ensure_claim_for_benefit(benefit_id, user_id)
    if not claim:
        raise HTTPException(status_code=404, detail="No claim for this benefit")
    return ClaimOut(**claim)


@router.patch("/{claim_id}", response_model=ClaimOut)
def update_claim(
    claim_id: str,
    body: ClaimUpdateRequest,
    user_id: str = Depends(get_current_user_id),
):
    store = get_store()
    updates = body.model_dump(exclude_unset=True)
    claim = store.update_claim(claim_id, user_id, updates)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimOut(**claim)


@router.post("/{claim_id}/submit", response_model=ClaimOut)
def submit_claim(
    claim_id: str,
    body: ClaimSubmitRequest,
    user_id: str = Depends(get_current_user_id),
):
    store = get_store()
    claim = store.submit_claim(
        claim_id,
        user_id,
        notes=body.customer_notes,
        prefilled=body.prefilled_data,
    )
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    return ClaimOut(**claim)


@router.post("/{claim_id}/documents")
async def upload_document(
    claim_id: str,
    file: UploadFile = File(...),
    document_type: str = "receipt",
    user_id: str = Depends(get_current_user_id),
):
    store = get_store()
    claim = store.get_claim(claim_id, user_id)
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")

    ext = Path(file.filename or "upload.bin").suffix or ".bin"
    name = f"{claim_id}_{uuid.uuid4().hex[:8]}{ext}"
    dest = UPLOAD_DIR / name
    content = await file.read()
    dest.write_bytes(content)

    file_url = f"/uploads/{name}"
    doc = store.add_document(
        claim_id=claim_id,
        file_url=file_url,
        file_name=file.filename or name,
        doc_type=document_type,
    )
    updated = store.get_claim(claim_id, user_id)
    return {"document": doc, "claim": updated}
