"""Keyword matching engine.

This is the only place that decides whether a post matches a tracker and the
only place that creates or removes Match records. Keeping it in one file
guarantees the same rules are used when a post is added and when a tracker
is created or edited.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Match, Post, Tracker
from app.models.mixins import utcnow
from app.schemas.common import LeadStatus, normalize_text
from app.services import notification_service


def find_matched_keywords(tracker: Tracker, post: Post) -> list[str]:
    """Return the tracker keywords found in the post (empty list = no match).

    Rules:
    1. The post platform must be one of the tracker platforms.
    2. If the text contains any excluded keyword, the post is rejected.
    3. Otherwise every keyword found as a substring counts.
    Text is compared in lowercase with collapsed whitespace.
    """
    if post.platform not in tracker.platforms:
        return []

    text = normalize_text(post.text)

    for excluded in tracker.excluded_keywords:
        if excluded in text:
            return []

    return [keyword for keyword in tracker.keywords if keyword in text]


def find_match(db: Session, tracker_id: int, post_id: int) -> Match | None:
    """Return the existing match for this tracker + post pair, if any."""
    return db.scalar(
        select(Match).where(Match.tracker_id == tracker_id, Match.post_id == post_id)
    )


def _create_match(db: Session, tracker: Tracker, post: Post, keywords: list[str]) -> Match:
    """Store a new match with status "new" and create its notification."""
    timestamp = utcnow()
    match = Match(
        tracker_id=tracker.id,
        post_id=post.id,
        matched_keywords=keywords,
        status=LeadStatus.NEW.value,
        created_at=timestamp,
        updated_at=timestamp,
    )
    db.add(match)
    db.flush()
    notification_service.create_for_match(db, match)
    return match


def remove_match(db: Session, match: Match) -> None:
    """Delete a match; its notifications are removed by ON DELETE CASCADE."""
    db.delete(match)
    db.flush()


def match_post(db: Session, post: Post) -> list[Match]:
    """Check a newly added post against every active tracker.

    Returns the matches that were created.
    """
    created = []
    for tracker in db.scalars(select(Tracker).where(Tracker.is_active).order_by(Tracker.id)):
        if find_match(db, tracker.id, post.id) is not None:
            continue  # never create a duplicate for the same pair
        keywords = find_matched_keywords(tracker, post)
        if keywords:
            created.append(_create_match(db, tracker, post, keywords))
    return created


def reevaluate_tracker(db: Session, tracker: Tracker) -> None:
    """Re-check all stored posts after a tracker was created or changed.

    - A match that no longer fits the new settings is removed
      (together with its notification).
    - A match that still fits is kept with its lead status; only the list of
      matched keywords is refreshed.
    - A post that fits now but had no match gets one, but only if the
      tracker is active. Inactive trackers never create matches.
    """
    existing_matches = {
        m.post_id: m for m in db.scalars(select(Match).where(Match.tracker_id == tracker.id))
    }
    for post in db.scalars(select(Post).order_by(Post.id)):
        keywords = find_matched_keywords(tracker, post)
        existing = existing_matches.get(post.id)

        if existing is not None and not keywords:
            remove_match(db, existing)
        elif existing is not None:
            existing.matched_keywords = keywords
        elif keywords and tracker.is_active:
            _create_match(db, tracker, post, keywords)
