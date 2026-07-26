"""Auth routes – demo login/signup + Supabase Auth when cloud primary."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import LoginRequest, ProfileOut, SignupRequest, TokenResponse
from app.services.demo_store import DEMO_EMAIL, DEMO_PASSWORD
from app.services.store import get_store, get_store_kind

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    store = get_store()
    result = store.authenticate(body.email, body.password)
    # Hybrid fallback: if supabase primary login fails, try local demo store
    if not result and get_store_kind() == "supabase":
        from app.services.demo_store import get_demo_store

        result = get_demo_store().authenticate(body.email, body.password)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(
        access_token=result["access_token"],
        user=ProfileOut(**result["user"]),
    )


@router.post("/signup", response_model=TokenResponse)
def signup(body: SignupRequest):
    store = get_store()
    try:
        result = store.signup(body.email, body.password, body.full_name)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return TokenResponse(
        access_token=result["access_token"],
        user=ProfileOut(**result["user"]),
    )


@router.get("/demo-credentials")
def demo_credentials():
    """Public helper for the login page."""
    return {
        "email": DEMO_EMAIL,
        "password": DEMO_PASSWORD,
        "note": "Use these credentials to explore the full demo with seed data.",
        "data_backend": get_store_kind(),
    }
