from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.api.responses import CONFLICT, NOT_FOUND
from app.schemas.common import Platform
from app.schemas.tracker import TrackerCreate, TrackerResponse, TrackerUpdate
from app.services import tracker_service

router = APIRouter(prefix="/api/trackers", tags=["Trackers"])


@router.get("", response_model=list[TrackerResponse], summary="List trackers")
def list_trackers(
    is_active: bool | None = Query(default=None, description="Only active or only paused"),
    platform: Platform | None = Query(default=None, description="Trackers watching this platform"),
    search: str | None = Query(default=None, description="Part of the tracker name"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return tracker_service.list_trackers(db, user, is_active, platform, search)


@router.post(
    "",
    response_model=TrackerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tracker",
    description="Creates a tracker and checks already stored posts against it.",
    responses=CONFLICT,
)
def create_tracker(
    data: TrackerCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return tracker_service.create_tracker(db, user, data)


@router.get(
    "/{tracker_id}",
    response_model=TrackerResponse,
    summary="Get one tracker",
    responses=NOT_FOUND,
)
def get_tracker(
    tracker_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return tracker_service.get_tracker(db, user, tracker_id)


@router.patch(
    "/{tracker_id}",
    response_model=TrackerResponse,
    summary="Update a tracker",
    description=(
        "Partial update. After the change all stored posts are re-evaluated: "
        "matches that no longer fit are removed, new ones are created if the "
        "tracker is active."
    ),
    responses={**NOT_FOUND, **CONFLICT},
)
def update_tracker(
    tracker_id: int,
    data: TrackerUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return tracker_service.update_tracker(db, user, tracker_id, data)


@router.delete(
    "/{tracker_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tracker",
    description="Also deletes the tracker's matches and their notifications.",
    responses=NOT_FOUND,
)
def delete_tracker(
    tracker_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    tracker_service.delete_tracker(db, user, tracker_id)
