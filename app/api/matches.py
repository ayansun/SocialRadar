from fastapi import APIRouter, Query

from app.api.responses import CONFLICT, NOT_FOUND
from app.schemas.common import LeadStatus, Platform
from app.schemas.match import MatchResponse, MatchStatusUpdate
from app.services import lead_service

router = APIRouter(prefix="/api/matches", tags=["Matches / Leads"])


@router.get(
    "",
    response_model=list[MatchResponse],
    summary="List matches (leads)",
    responses=NOT_FOUND,
)
def list_matches(
    platform: Platform | None = Query(default=None),
    tracker_id: int | None = Query(default=None, description="404 if the tracker does not exist"),
    status: LeadStatus | None = Query(default=None),
    search: str | None = Query(default=None, description="Part of the post text or author"),
):
    return lead_service.list_matches(platform, tracker_id, status, search)


@router.get(
    "/{match_id}", response_model=MatchResponse, summary="Get one match", responses=NOT_FOUND
)
def get_match(match_id: int):
    return lead_service.get_match(match_id)


@router.patch(
    "/{match_id}/status",
    response_model=MatchResponse,
    summary="Change lead status",
    description=(
        "Allowed transitions: new → saved | dismissed, saved → contacted | "
        "dismissed, contacted → dismissed, dismissed → new. Anything else "
        "returns 409. Sending the current status again changes nothing."
    ),
    responses={**NOT_FOUND, **CONFLICT},
)
def update_match_status(match_id: int, data: MatchStatusUpdate):
    return lead_service.update_status(match_id, data.status)
