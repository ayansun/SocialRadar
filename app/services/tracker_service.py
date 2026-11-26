"""Tracker management (Workflow 1)."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import BusinessRuleError, ConflictError, NotFoundError
from app.models import Tracker, User
from app.models.mixins import utcnow
from app.schemas.common import Platform
from app.schemas.tracker import TrackerCreate, TrackerUpdate
from app.services import matching_service
from app.services.common import count_matches, ensure_access


def to_response(db: Session, tracker: Tracker) -> dict:
    return {
        "id": tracker.id,
        "name": tracker.name,
        "keywords": tracker.keywords,
        "excluded_keywords": tracker.excluded_keywords,
        "platforms": tracker.platforms,
        "is_active": tracker.is_active,
        "match_count": count_matches(db, tracker_id=tracker.id),
        "created_at": tracker.created_at,
        "updated_at": tracker.updated_at,
    }


def _get(db: Session, user: User, tracker_id: int) -> Tracker:
    """404 if missing, 403 if it belongs to someone else (admins may access all)."""
    tracker = db.get(Tracker, tracker_id)
    if tracker is None:
        raise NotFoundError("Tracker not found")
    ensure_access(user, tracker.owner_id)
    return tracker


def _check_name_is_free(db: Session, name: str, ignore_id: int | None = None) -> None:
    """Tracker names must be unique (case-insensitive)."""
    query = select(Tracker.id).where(func.lower(Tracker.name) == name.lower())
    if ignore_id is not None:
        query = query.where(Tracker.id != ignore_id)
    if db.scalar(query) is not None:
        raise ConflictError("Tracker with this name already exists")


def list_trackers(
    db: Session,
    user: User,
    is_active: bool | None = None,
    platform: Platform | None = None,
    search: str | None = None,
) -> list[dict]:
    query = select(Tracker).order_by(Tracker.id)
    if user.role != "admin":
        query = query.where(Tracker.owner_id == user.id)  # only own trackers
    if is_active is not None:
        query = query.where(Tracker.is_active == is_active)
    if platform is not None:
        # JSONB containment: platforms @> '["bluesky"]'
        query = query.where(Tracker.platforms.contains([platform.value]))
    if search:
        query = query.where(
            func.lower(Tracker.name).contains(search.lower().strip(), autoescape=True)
        )
    return [to_response(db, t) for t in db.scalars(query)]


def get_tracker(db: Session, user: User, tracker_id: int) -> dict:
    return to_response(db, _get(db, user, tracker_id))


def create_tracker(db: Session, user: User, data: TrackerCreate) -> dict:
    _check_name_is_free(db, data.name)

    # mode="json" turns enums into plain strings like "bluesky"
    tracker = Tracker(**data.model_dump(mode="json"), owner_id=user.id)
    db.add(tracker)
    try:
        db.flush()
    except IntegrityError:  # two requests with the same name at once
        db.rollback()
        raise ConflictError("Tracker with this name already exists")

    # Posts that are already stored are checked against the new tracker.
    matching_service.reevaluate_tracker(db, tracker)
    db.commit()
    return to_response(db, tracker)


def update_tracker(db: Session, user: User, tracker_id: int, data: TrackerUpdate) -> dict:
    tracker = _get(db, user, tracker_id)
    # Only the fields that the client actually sent.
    changes = data.model_dump(mode="json", exclude_unset=True)

    if "name" in changes:
        _check_name_is_free(db, changes["name"], ignore_id=tracker_id)

    # The schema checks overlap only when both lists are sent together,
    # so check again against the values that will actually be stored.
    keywords = changes.get("keywords", tracker.keywords)
    excluded = changes.get("excluded_keywords", tracker.excluded_keywords)
    overlap = [word for word in keywords if word in excluded]
    if overlap:
        raise BusinessRuleError(
            f"A keyword cannot also be an excluded keyword: {', '.join(overlap)}"
        )

    for field, value in changes.items():
        setattr(tracker, field, value)
    tracker.updated_at = utcnow()

    try:
        db.flush()
    except IntegrityError:
        db.rollback()
        raise ConflictError("Tracker with this name already exists")

    # Keep existing matches consistent with the new settings.
    matching_service.reevaluate_tracker(db, tracker)
    db.commit()
    return to_response(db, tracker)


def delete_tracker(db: Session, user: User, tracker_id: int) -> None:
    tracker = _get(db, user, tracker_id)
    # The database removes the tracker's matches and their notifications
    # (ON DELETE CASCADE), so nothing is left pointing to a missing tracker.
    db.delete(tracker)
    db.commit()
