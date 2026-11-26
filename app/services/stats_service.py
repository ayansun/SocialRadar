"""Numbers for the dashboard."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, Post, Tracker, User
from app.services import lead_service, notification_service

RECENT_MATCHES_LIMIT = 5


def get_stats(db: Session, user: User) -> dict:
    """Numbers for the user's own trackers and leads (admins: everything).
    Posts are shared by everyone, so they are counted in full."""
    trackers = select(func.count(Tracker.id))
    matches = select(func.count(Match.id))
    if user.role != "admin":
        trackers = trackers.where(Tracker.owner_id == user.id)
        matches = matches.join(Tracker, Match.tracker_id == Tracker.id).where(
            Tracker.owner_id == user.id
        )
    return {
        "trackers_total": db.scalar(trackers) or 0,
        "trackers_active": db.scalar(trackers.where(Tracker.is_active)) or 0,
        "posts_total": db.scalar(select(func.count(Post.id))) or 0,
        "matches_total": db.scalar(matches) or 0,
        "notifications_unread": notification_service.count_unread(db, user),
        "recent_matches": lead_service.list_matches(db, user, limit=RECENT_MATCHES_LIMIT),
    }
