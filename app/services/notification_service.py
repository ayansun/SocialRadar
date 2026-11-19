"""Notifications: one is created automatically for every new match."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.errors import NotFoundError
from app.models import Match, Notification
from app.services.common import post_view


def to_response(db: Session, notification: Notification) -> dict:
    """Add the message text and the related post to a notification.

    The message is built here (not stored) so it always shows the current
    tracker name, even after the tracker is renamed.
    """
    match = notification.match
    message = (
        f'New lead for "{match.tracker.name}": '
        f"{match.post.author} on {match.post.platform.capitalize()}"
    )
    return {
        "id": notification.id,
        "match_id": match.id,
        "tracker_id": match.tracker_id,
        "post_id": match.post_id,
        "message": message,
        "post": post_view(db, match.post),
        "is_read": notification.is_read,
        "created_at": notification.created_at,
    }


def create_for_match(db: Session, match: Match) -> Notification:
    """Create an unread notification for a new match."""
    notification = Notification(match_id=match.id, is_read=False)
    db.add(notification)
    db.flush()
    return notification


def _get(db: Session, notification_id: int) -> Notification:
    notification = db.get(Notification, notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")
    return notification


def list_notifications(db: Session, is_read: bool | None = None) -> list[dict]:
    """Newest first, optionally filtered by read state."""
    query = select(Notification).order_by(Notification.id.desc())
    if is_read is not None:
        query = query.where(Notification.is_read == is_read)
    return [to_response(db, n) for n in db.scalars(query)]


def count_unread(db: Session) -> int:
    return db.scalar(
        select(func.count(Notification.id)).where(Notification.is_read.is_(False))
    ) or 0


def set_read(db: Session, notification_id: int, is_read: bool) -> dict:
    notification = _get(db, notification_id)
    notification.is_read = is_read
    db.commit()
    return to_response(db, notification)


def delete_notification(db: Session, notification_id: int) -> None:
    notification = _get(db, notification_id)
    db.delete(notification)
    db.commit()
