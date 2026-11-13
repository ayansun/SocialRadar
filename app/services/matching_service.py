from app.schemas.common import LeadStatus, normalize_text
from app.services import notification_service
from app.storage import now, storage


def find_matched_keywords(tracker: dict, post: dict) -> list[str]:
    """Return the tracker keywords found in the post (empty list = no match).

    Rules:
    1. The post platform must be one of the tracker platforms.
    2. If the text contains any excluded keyword, the post is rejected.
    3. Otherwise every keyword found as a substring counts.
    Text is compared in lowercase with collapsed whitespace.
    """
    if post["platform"] not in tracker["platforms"]:
        return []

    text = normalize_text(post["text"])

    for excluded in tracker["excluded_keywords"]:
        if excluded in text:
            return []

    return [keyword for keyword in tracker["keywords"] if keyword in text]


def find_match(tracker_id: int, post_id: int) -> dict | None:
    """Return the existing match for this tracker + post pair, if any."""
    for match in storage.matches.values():
        if match["tracker_id"] == tracker_id and match["post_id"] == post_id:
            return match
    return None


def _create_match(tracker: dict, post: dict, keywords: list[str]) -> dict:
    """Store a new match with status "new" and create its notification."""
    timestamp = now()
    match = {
        "id": storage.next_id("match"),
        "tracker_id": tracker["id"],
        "post_id": post["id"],
        "matched_keywords": keywords,
        "status": LeadStatus.NEW.value,
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    storage.matches[match["id"]] = match
    notification_service.create_for_match(match)
    return match


def remove_match(match_id: int) -> None:
    """Delete a match together with its notifications."""
    notification_service.delete_for_match(match_id)
    del storage.matches[match_id]


def remove_matches_for_tracker(tracker_id: int) -> None:
    for match in list(storage.matches.values()):
        if match["tracker_id"] == tracker_id:
            remove_match(match["id"])


def remove_matches_for_post(post_id: int) -> None:
    for match in list(storage.matches.values()):
        if match["post_id"] == post_id:
            remove_match(match["id"])


def match_post(post: dict) -> list[dict]:
    """Check a newly added post against every active tracker.

    Returns the matches that were created.
    """
    created = []
    for tracker in storage.trackers.values():
        if not tracker["is_active"]:
            continue
        if find_match(tracker["id"], post["id"]) is not None:
            continue  # never create a duplicate for the same pair
        keywords = find_matched_keywords(tracker, post)
        if keywords:
            created.append(_create_match(tracker, post, keywords))
    return created


def reevaluate_tracker(tracker: dict) -> None:
    """Re-check all stored posts after a tracker was created or changed.

    - A match that no longer fits the new settings is removed
      (together with its notification).
    - A match that still fits is kept with its lead status; only the list of
      matched keywords is refreshed.
    - A post that fits now but had no match gets one, but only if the
      tracker is active. Inactive trackers never create matches.
    """
    for post in list(storage.posts.values()):
        keywords = find_matched_keywords(tracker, post)
        existing = find_match(tracker["id"], post["id"])

        if existing is not None and not keywords:
            remove_match(existing["id"])
        elif existing is not None:
            existing["matched_keywords"] = keywords
        elif keywords and tracker["is_active"]:
            _create_match(tracker, post, keywords)
