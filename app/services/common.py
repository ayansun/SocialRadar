"""Small helpers used by several services."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Match, Post


def count_matches(db: Session, tracker_id: int | None = None, post_id: int | None = None) -> int:
    """Count matches that belong to a tracker and/or a post."""
    query = select(func.count(Match.id))
    if tracker_id is not None:
        query = query.where(Match.tracker_id == tracker_id)
    if post_id is not None:
        query = query.where(Match.post_id == post_id)
    return db.scalar(query) or 0


def post_view(db: Session, post: Post) -> dict:
    """Post plus its computed match_count (shape of PostResponse)."""
    return {
        "id": post.id,
        "platform": post.platform,
        "external_id": post.external_id,
        "author": post.author,
        "text": post.text,
        "url": post.url,
        "source": post.source,
        "match_count": count_matches(db, post_id=post.id),
        "created_at": post.created_at,
    }
