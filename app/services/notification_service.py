"""Notifications: one is created automatically for every new match."""

from app.errors import NotFoundError
from app.services.common import post_view
from app.storage import now, storage


def to_response(notification: dict) -> dict:
    """Add the message text and the related post to a notification record.

    The message is built here (not stored) so it always shows the current
    tracker name, even after the tracker is renamed.
    """
    tracker = storage.trackers[notification["tracker_id"]]
    post = storage.posts[notification["post_id"]]
    message = (
        f'New lead for "{tracker["name"]}": '
        f'{post["author"]} on {post["platform"].capitalize()}'
    )
    return {**notification, "message": message, "post": post_view(post)}


def create_for_match(match: dict) -> dict:
    """Create an unread notification for a new match."""
    notification = {
        "id": storage.next_id("notification"),
        "match_id": match["id"],
        "tracker_id": match["tracker_id"],
        "post_id": match["post_id"],
        "is_read": False,
        "created_at": now(),
    }
    storage.notifications[notification["id"]] = notification
    return notification


def delete_for_match(match_id: int) -> None:
    """Remove notifications that point to a match which is being deleted."""
    for notification in list(storage.notifications.values()):
        if notification["match_id"] == match_id:
            del storage.notifications[notification["id"]]


def _get(notification_id: int) -> dict:
    notification = storage.notifications.get(notification_id)
    if notification is None:
        raise NotFoundError("Notification not found")
    return notification


def list_notifications(is_read: bool | None = None) -> list[dict]:
    """Newest first, optionally filtered by read state."""
    notifications = sorted(
        storage.notifications.values(), key=lambda n: n["id"], reverse=True
    )
    if is_read is not None:
        notifications = [n for n in notifications if n["is_read"] == is_read]
    return [to_response(n) for n in notifications]


def count_unread() -> int:
    return sum(1 for n in storage.notifications.values() if not n["is_read"])


def set_read(notification_id: int, is_read: bool) -> dict:
    notification = _get(notification_id)
    notification["is_read"] = is_read
    return to_response(notification)


def delete_notification(notification_id: int) -> None:
    _get(notification_id)
    del storage.notifications[notification_id]
