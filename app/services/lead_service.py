"""Lead processing (Workflow 3).

Every match is a potential client (a lead) with a status. This service
lists leads and controls how their status is allowed to change.
"""

from app.errors import ConflictError, NotFoundError
from app.schemas.common import LeadStatus, Platform
from app.services.common import post_view
from app.storage import now, storage

# Which statuses a lead can move to from each status.
# Note: dismissed -> contacted is not allowed. A dismissed lead must be
# restored to "new" first.
ALLOWED_TRANSITIONS: dict[str, list[str]] = {
    "new": ["saved", "dismissed"],
    "saved": ["contacted", "dismissed"],
    "contacted": ["dismissed"],
    "dismissed": ["new"],
}


def to_response(match: dict) -> dict:
    """Add tracker name, post and allowed next statuses to a match record."""
    tracker = storage.trackers[match["tracker_id"]]
    post = storage.posts[match["post_id"]]
    return {
        **match,
        "tracker_name": tracker["name"],
        "post": post_view(post),
        "allowed_statuses": ALLOWED_TRANSITIONS[match["status"]],
    }


def _get(match_id: int) -> dict:
    match = storage.matches.get(match_id)
    if match is None:
        raise NotFoundError("Match not found")
    return match


def list_matches(
    platform: Platform | None = None,
    tracker_id: int | None = None,
    status: LeadStatus | None = None,
    search: str | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Newest first, with optional filters."""
    if tracker_id is not None and tracker_id not in storage.trackers:
        raise NotFoundError("Tracker not found")

    needle = search.lower().strip() if search else None
    result = []
    for match in sorted(storage.matches.values(), key=lambda m: m["id"], reverse=True):
        post = storage.posts[match["post_id"]]
        if platform is not None and post["platform"] != platform.value:
            continue
        if tracker_id is not None and match["tracker_id"] != tracker_id:
            continue
        if status is not None and match["status"] != status.value:
            continue
        if needle and needle not in f'{post["text"]} {post["author"]}'.lower():
            continue
        result.append(to_response(match))
        if limit is not None and len(result) == limit:
            break
    return result


def get_match(match_id: int) -> dict:
    return to_response(_get(match_id))


def update_status(match_id: int, new_status: LeadStatus) -> dict:
    match = _get(match_id)
    current = match["status"]

    # Repeating the same status is harmless: nothing changes.
    if new_status.value == current:
        return to_response(match)

    if new_status.value not in ALLOWED_TRANSITIONS[current]:
        raise ConflictError(
            f"Invalid lead status transition: {current} -> {new_status.value}"
        )

    match["status"] = new_status.value
    match["updated_at"] = now()
    return to_response(match)
