from fastapi import APIRouter

from app.schemas import HealthResponse
from app.settings import BACKEND_ROOT


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def healthcheck() -> HealthResponse:
    return HealthResponse(status="ok", backend_root=str(BACKEND_ROOT))
