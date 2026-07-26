"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, EmailStr, Field


# ── Auth ──────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "ProfileOut"


class ProfileOut(BaseModel):
    id: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Cards & Transactions ──────────────────────────────────────────────

class CardOut(BaseModel):
    id: str
    card_name: str
    card_type: str
    last_four: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None


class TransactionOut(BaseModel):
    id: str
    merchant_raw: str
    merchant_normalized: Optional[str] = None
    amount: float
    currency: str = "INR"
    transaction_date: datetime
    mcc: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    card_id: Optional[str] = None


class TransactionCreate(BaseModel):
    """Inject a new transaction to test the live agent pipeline."""
    merchant_raw: str = Field(..., examples=["AMZN MKTP IN *LAPTOP99"])
    amount: float = Field(..., gt=0, examples=[89999.0])
    description: Optional[str] = Field(default="", examples=["Dell XPS 14 Laptop"])
    category: Optional[str] = Field(
        default=None,
        description="Optional hint. Leave empty to let Transaction Intelligence classify.",
        examples=["Electronics"],
    )
    mcc: Optional[str] = None
    currency: str = "INR"
    run_detection: bool = Field(
        default=True,
        description="If true, immediately run the LangGraph agent pipeline and save results.",
    )


# ── Detected Benefits ─────────────────────────────────────────────────

class DetectedBenefitOut(BaseModel):
    id: str
    transaction_id: str
    benefit_type: str
    confidence_score: Optional[float] = None
    status: str = "detected"
    explanation: Optional[str] = None
    policy_reference: Optional[str] = None
    coverage_window_days: Optional[int] = None
    max_coverage_amount: Optional[float] = None
    created_at: Optional[datetime] = None
    # Joined fields for UI convenience
    merchant: Optional[str] = None
    amount: Optional[float] = None
    transaction_date: Optional[datetime] = None
    category: Optional[str] = None


class DetectedBenefitDetail(DetectedBenefitOut):
    transaction: Optional[TransactionOut] = None
    claim: Optional["ClaimOut"] = None
    prefilled_data: Optional[dict[str, Any]] = None
    missing_documents: Optional[list[str]] = None
    confidence_breakdown: Optional[dict[str, Any]] = None


# ── Claims ────────────────────────────────────────────────────────────

class ClaimOut(BaseModel):
    id: str
    detected_benefit_id: str
    status: str = "draft"
    prefilled_data: Optional[dict[str, Any]] = None
    missing_documents: Optional[list[str]] = None
    customer_notes: Optional[str] = None
    submitted_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ClaimUpdateRequest(BaseModel):
    customer_notes: Optional[str] = None
    prefilled_data: Optional[dict[str, Any]] = None
    missing_documents: Optional[list[str]] = None


class ClaimSubmitRequest(BaseModel):
    customer_notes: Optional[str] = None
    prefilled_data: Optional[dict[str, Any]] = None


# ── Assistant ─────────────────────────────────────────────────────────

class AssistantRequest(BaseModel):
    message: str
    claim_id: Optional[str] = None
    benefit_id: Optional[str] = None
    conversation_history: Optional[list[dict[str, str]]] = None


class AssistantResponse(BaseModel):
    reply: str
    citations: list[str] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)


# Resolve forward refs
TokenResponse.model_rebuild()
DetectedBenefitDetail.model_rebuild()
