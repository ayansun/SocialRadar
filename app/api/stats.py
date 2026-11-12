from fastapi import APIRouter

from app.schemas.stats import StatsResponse
from app.services import stats_service

router = APIRouter(tags=["Other"])


@router.get("/api/stats", response_model=StatsResponse, summary="Dashboard numbers")
def get_stats():
    return stats_service.get_stats()


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}
