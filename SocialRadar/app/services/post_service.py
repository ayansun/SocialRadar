"""Post ingestion (Workflow 2).

`create_post` is the single entry point for new posts. The manual API
endpoint and the demo import both call it. A future Bluesky or Threads
integration would call it too, with its own `source` value.
"""

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.errors import ConflictError, NotFoundError
from app.models import Match, Post
from app.schemas.common import Platform, PostSource
from app.schemas.post import PostCreate
from app.services import lead_service, matching_service
from app.services.common import post_view


def _get(db: Session, post_id: int) -> Post:
    post = db.get(Post, post_id)
    if post is None:
        raise NotFoundError("Post not found")
    return post


def list_posts(
    db: Session,
    platform: Platform | None = None,
    source: PostSource | None = None,
    search: str | None = None,
    has_matches: bool | None = None,
) -> list[dict]:
    """Newest first, with optional filters."""
    query = select(Post).order_by(Post.id.desc())
    if platform is not None:
        query = query.where(Post.platform == platform.value)
    if source is not None:
        query = query.where(Post.source == source.value)
    if search and search.strip():
        needle = search.lower().strip()
        escaped = needle.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        query = query.where((Post.text + " " + Post.author).ilike(f"%{escaped}%", escape="\\"))
    if has_matches is not None:
        has_any = select(Match.id).where(Match.post_id == Post.id).exists()
        query = query.where(has_any if has_matches else ~has_any)
    return [post_view(db, p) for p in db.scalars(query)]


def get_post(db: Session, post_id: int) -> dict:
    return post_view(db, _get(db, post_id))


def create_post(db: Session, data: PostCreate, source: PostSource = PostSource.MANUAL) -> dict:
    """Save a post, run keyword matching and return what happened."""
    # The same post must not be stored twice.
    existing = db.scalar(
        select(Post.id).where(
            Post.platform == data.platform.value, Post.external_id == data.external_id
        )
    )
    if existing is not None:
        raise ConflictError("Post already exists")

    post = Post(
        platform=data.platform.value,
        external_id=data.external_id,
        author=data.author,
        text=data.text,
        url=str(data.url),
        source=source.value,
    )
    db.add(post)
    try:
        db.flush()
    except IntegrityError:  # the same post arrived in two requests at once
        db.rollback()
        raise ConflictError("Post already exists")

    # Each new match also creates exactly one notification.
    new_matches = matching_service.match_post(db, post)
    db.commit()

    return {
        "post": post_view(db, post),
        "matches_created": len(new_matches),
        "notifications_created": len(new_matches),
        "matches": [lead_service.to_response(db, m) for m in new_matches],
    }


def delete_post(db: Session, post_id: int) -> None:
    post = _get(db, post_id)
    # Matches and their notifications are removed by ON DELETE CASCADE.
    db.delete(post)
    db.commit()
