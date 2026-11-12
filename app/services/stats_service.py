"""Numbers for the dashboard."""

from app.services import lead_service, notification_service
from app.storage import storage

RECENT_MATCHES_LIMIT = 5


def get_stats() -> dict:
    trackers = storage.trackers.values()
    return {
        "trackers_total": len(trackers),
        "trackers_active": sum(1 for t in trackers if t["is_active"]),
        "posts_total": len(storage.posts),
        "matches_total": len(storage.matches),
        "notifications_unread": notification_service.count_unread(),
        "recent_matches": lead_service.list_matches(limit=RECENT_MATCHES_LIMIT),
    }
