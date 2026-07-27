"""Auth routes — Supabase Auth only."""

from fastapi import APIRouter, HTTPException, status

from app.models.schemas import LoginRequest, ProfileOut, SignupRequest, TokenResponse
from app.services.store import get_store

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest):
    store = get_store()
    result = store.authenticate(body.email, body.password)
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
