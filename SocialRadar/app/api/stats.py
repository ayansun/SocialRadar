from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.stats import StatsResponse
from app.services import stats_service

router = APIRouter(tags=["Other"])


@router.get("/api/stats", response_model=StatsResponse, summary="Dashboard numbers")
def get_stats(db: Session = Depends(get_db)):
    return stats_service.get_stats(db)


@router.get("/health", summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}
