"""Numbers for the dashboard."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, Post, Tracker
from app.services import lead_service, notification_service

RECENT_MATCHES_LIMIT = 5


def get_stats(db: Session) -> dict:
    return {
        "trackers_total": db.scalar(select(func.count(Tracker.id))) or 0,
        "trackers_active": db.scalar(
            select(func.count(Tracker.id)).where(Tracker.is_active)
        )
        or 0,
        "posts_total": db.scalar(select(func.count(Post.id))) or 0,
        "matches_total": db.scalar(select(func.count(Match.id))) or 0,
        "notifications_unread": notification_service.count_unread(db),
        "recent_matches": lead_service.list_matches(db, limit=RECENT_MATCHES_LIMIT),
    }
