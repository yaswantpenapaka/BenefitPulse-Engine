"""Authentication dependency – demo tokens or Supabase JWT."""

from __future__ import annotations

from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from app.services.demo_store import get_demo_store
from app.services.store import get_store

security = HTTPBearer(auto_error=False)


async def get_current_user_id(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )
    token = credentials.credentials
    settings = get_settings()

    # Active store (demo or supabase) first
    try:
        user_id = get_store().user_id_from_token(token)
        if user_id:
            return user_id
    except Exception:
        pass

    # Demo tokens always accepted as fallback (local hybrid demos)
    user_id = get_demo_store().user_id_from_token(token)
    if user_id:
        return user_id

    # Explicit Supabase JWT validation
    if settings.has_supabase and settings.supabase_jwt_secret:
        try:
            import jwt

            payload = jwt.decode(
                token,
                settings.supabase_jwt_secret,
                algorithms=["HS256"],
                audience="authenticated",
            )
            uid = payload.get("sub")
            if uid:
                return uid
        except Exception:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token",
    )
