from .auth import router as auth_router
from .benefits import router as benefits_router
from .claims import router as claims_router
from .assistant import router as assistant_router
from .dashboard import router as dashboard_router

__all__ = [
    "auth_router",
    "benefits_router",
    "claims_router",
    "assistant_router",
    "dashboard_router",
]
