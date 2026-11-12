"""Tracker management (Workflow 1)."""

from app.errors import BusinessRuleError, ConflictError, NotFoundError
from app.schemas.common import Platform
from app.schemas.tracker import TrackerCreate, TrackerUpdate
from app.services import matching_service
from app.services.common import count_matches
from app.storage import now, storage


def to_response(tracker: dict) -> dict:
    return {**tracker, "match_count": count_matches(tracker_id=tracker["id"])}


def _get(tracker_id: int) -> dict:
    tracker = storage.trackers.get(tracker_id)
    if tracker is None:
        raise NotFoundError("Tracker not found")
    return tracker


def _check_name_is_free(name: str, ignore_id: int | None = None) -> None:
    """Tracker names must be unique (case-insensitive)."""
    for tracker in storage.trackers.values():
        if tracker["id"] != ignore_id and tracker["name"].lower() == name.lower():
            raise ConflictError("Tracker with this name already exists")


def list_trackers(
    is_active: bool | None = None,
    platform: Platform | None = None,
    search: str | None = None,
) -> list[dict]:
    trackers = list(storage.trackers.values())
    if is_active is not None:
        trackers = [t for t in trackers if t["is_active"] == is_active]
    if platform is not None:
        trackers = [t for t in trackers if platform.value in t["platforms"]]
    if search:
        needle = search.lower().strip()
        trackers = [t for t in trackers if needle in t["name"].lower()]
    return [to_response(t) for t in trackers]


def get_tracker(tracker_id: int) -> dict:
    return to_response(_get(tracker_id))


def create_tracker(data: TrackerCreate) -> dict:
    _check_name_is_free(data.name)

    timestamp = now()
    tracker = {
        "id": storage.next_id("tracker"),
        # mode="json" turns enums into plain strings like "bluesky"
        **data.model_dump(mode="json"),
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    storage.trackers[tracker["id"]] = tracker

    # Posts that are already stored are checked against the new tracker.
    matching_service.reevaluate_tracker(tracker)
    return to_response(tracker)


def update_tracker(tracker_id: int, data: TrackerUpdate) -> dict:
    tracker = _get(tracker_id)
    # Only the fields that the client actually sent.
    changes = data.model_dump(mode="json", exclude_unset=True)

    if "name" in changes:
        _check_name_is_free(changes["name"], ignore_id=tracker_id)

    # The schema checks overlap only when both lists are sent together,
    # so check again against the values that will actually be stored.
    keywords = changes.get("keywords", tracker["keywords"])
    excluded = changes.get("excluded_keywords", tracker["excluded_keywords"])
    overlap = [word for word in keywords if word in excluded]
    if overlap:
        raise BusinessRuleError(
            f"A keyword cannot also be an excluded keyword: {', '.join(overlap)}"
        )

    tracker.update(changes)
    tracker["updated_at"] = now()

    # Keep existing matches consistent with the new settings.
    matching_service.reevaluate_tracker(tracker)
    return to_response(tracker)


def delete_tracker(tracker_id: int) -> None:
    _get(tracker_id)
    # Remove matches and their notifications first, so nothing is left
    # pointing to a tracker that no longer exists.
    matching_service.remove_matches_for_tracker(tracker_id)
    del storage.trackers[tracker_id]
