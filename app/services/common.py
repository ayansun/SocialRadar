"""Small helpers used by several services."""

from app.storage import storage


def count_matches(tracker_id: int | None = None, post_id: int | None = None) -> int:
    """Count matches that belong to a tracker and/or a post."""
    count = 0
    for match in storage.matches.values():
        if tracker_id is not None and match["tracker_id"] != tracker_id:
            continue
        if post_id is not None and match["post_id"] != post_id:
            continue
        count += 1
    return count


def post_view(post: dict) -> dict:
    """Post record plus its computed match_count (shape of PostResponse)."""
    return {**post, "match_count": count_matches(post_id=post["id"])}
