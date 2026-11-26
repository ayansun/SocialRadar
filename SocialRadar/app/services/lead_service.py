"""Lead processing (Workflow 3).

Every match is a potential client (a lead) with a status. This service
lists leads and controls how their status is allowed to change.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Match, Post, Tracker
from app.models.mixins import utcnow
from app.schemas.common import LeadStatus, Platform
from app.services.common import post_view

# Which statuses a lead can move to from each status.
# Note: dismissed -> contacted is not allowed. A dismissed lead must be
# restored to "new" first.
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "new": ["saved", "dismissed"],
    "saved": ["contacted", "dismissed"],
    "contacted": ["dismissed"],
    "dismissed": ["new"],
}


def to_response(db: Session, match: Match) -> dict:
    """Add tracker name, post and allowed next statuses to a match."""
    return {
        "id": match.id,
        "tracker_id": match.tracker_id,
        "tracker_name": match.tracker.name,
        "post_id": match.post_id,
        "post": post_view(db, match.post),
        "matched_keywords": match.matched_keywords,
        "status": match.status,
        "allowed_statuses": ALLOWED_TRANSITIONS[match.status],
        "created_at": match.created_at,
        "updated_at": match.updated_at,
    }


def _get(db: Session, match_id: int) -> Match:
    match = db.get(Match, match_id)
    if match is None:
        raise NotFoundError("Match not found")
    return match


def list_matches(
    db: Session,
    platform: Platform | None = None,
    tracker_id: int | None = None,
    status: LeadStatus | None = None,
    search: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Newest first, with optional filters."""
    if tracker_id is not None and db.get(Tracker, tracker_id) is None:
        raise NotFoundError("Tracker not found")

    query = select(Match).join(Post, Match.post_id == Post.id).order_by(Match.id.desc())
    if platform is not None:
        query = query.where(Post.platform == platform.value)
    if tracker_id is not None:
        query = query.where(Match.tracker_id == tracker_id)
    if status is not None:
        query = query.where(Match.status == status.value)
    if search and search.strip():
        needle = search.lower().strip()
        query = query.where(
            (Post.text + " " + Post.author).ilike(f"%{_escape_like(needle)}%", escape="\\")
        )
    if limit is not None:
        query = query.limit(limit)
    return [to_response(db, m) for m in db.scalars(query)]


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def get_match(db: Session, match_id: int) -> dict:
    return to_response(db, _get(db, match_id))


def update_status(db: Session, match_id: int, new_status: LeadStatus) -> dict:
    match = _get(db, match_id)
    current = match.status

    # Repeating the same status is harmless: nothing changes.
    if new_status.value == current:
        return to_response(db, match)

    if new_status.value not in ALLOWED_TRANSITIONS[current]:
        raise ConflictError(
            f"Invalid lead status transition: {current} -> {new_status.value}"
        )

    match.status = new_status.value
    match.updated_at = utcnow()
    db.commit()
    return to_response(db, match)
