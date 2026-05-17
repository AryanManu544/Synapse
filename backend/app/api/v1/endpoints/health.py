from fastapi import APIRouter

from app.models.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Liveness probe for orchestration and load balancers."""
    return HealthResponse(status="ok")
