"""Dashboard aggregate + cards / transactions."""

from fastapi import APIRouter, Depends

from app.models.schemas import CardOut, ProfileOut, TransactionOut
from app.services.auth import get_current_user_id
from app.services.store import get_store

router = APIRouter(tags=["dashboard"])


@router.get("/me", response_model=ProfileOut)
def get_me(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    profile = store.get_profile(user_id)
    if not profile:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Profile not found")
    return ProfileOut(**profile)


@router.get("/cards", response_model=list[CardOut])
def list_cards(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    return [CardOut(**c) for c in store.get_cards(user_id)]


@router.get("/transactions", response_model=list[TransactionOut])
def list_transactions(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    return [TransactionOut(**t) for t in store.get_transactions(user_id)]


@router.get("/dashboard")
def dashboard_summary(user_id: str = Depends(get_current_user_id)):
    store = get_store()
    profile = store.get_profile(user_id)
    cards = store.get_cards(user_id)
    transactions = store.get_transactions(user_id)
    benefits = store.get_benefits(user_id)
    claims = store.get_claims(user_id)

    active_benefits = [b for b in benefits if b.get("status") in ("detected", "prefilled")]
    submitted = [c for c in claims if c.get("status") == "submitted"]

    return {
        "profile": profile,
        "cards": cards,
        "transactions": transactions[:10],
        "detected_benefits": benefits,
        "stats": {
            "cards_count": len(cards),
            "transactions_count": len(transactions),
            "active_benefits": len(active_benefits),
            "submitted_claims": len(submitted),
            "potential_coverage": sum(
                float(b.get("max_coverage_amount") or 0)
                for b in active_benefits
            ),
        },
    }
