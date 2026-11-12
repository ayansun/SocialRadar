"""Post ingestion (Workflow 2).

`create_post` is the single entry point for new posts. The manual API
endpoint and the demo import both call it. A future Bluesky or Threads
integration would call it too, with its own `source` value.
"""

from app.errors import ConflictError, NotFoundError
from app.schemas.common import Platform, PostSource
from app.schemas.post import PostCreate
from app.services import lead_service, matching_service
from app.services.common import post_view
from app.storage import now, storage


def _get(post_id: int) -> dict:
    post = storage.posts.get(post_id)
    if post is None:
        raise NotFoundError("Post not found")
    return post


def list_posts(
    platform: Platform | None = None,
    source: PostSource | None = None,
    search: str | None = None,
    has_matches: bool | None = None,
) -> list[dict]:
    """Newest first, with optional filters."""
    posts = sorted(storage.posts.values(), key=lambda p: p["id"], reverse=True)
    if platform is not None:
        posts = [p for p in posts if p["platform"] == platform.value]
    if source is not None:
        posts = [p for p in posts if p["source"] == source.value]
    if search:
        needle = search.lower().strip()
        posts = [p for p in posts if needle in f'{p["text"]} {p["author"]}'.lower()]

    result = [post_view(p) for p in posts]
    if has_matches is not None:
        result = [p for p in result if (p["match_count"] > 0) == has_matches]
    return result


def get_post(post_id: int) -> dict:
    return post_view(_get(post_id))


def create_post(data: PostCreate, source: PostSource = PostSource.MANUAL) -> dict:
    """Save a post, run keyword matching and return what happened."""
    # The same post must not be stored twice.
    for existing in storage.posts.values():
        if (
            existing["platform"] == data.platform.value
            and existing["external_id"] == data.external_id
        ):
            raise ConflictError("Post already exists")

    post = {
        "id": storage.next_id("post"),
        "platform": data.platform.value,
        "external_id": data.external_id,
        "author": data.author,
        "text": data.text,
        "url": str(data.url),
        "source": source.value,
        "created_at": now(),
    }
    storage.posts[post["id"]] = post

    # Each new match also creates exactly one notification.
    new_matches = matching_service.match_post(post)

    return {
        "post": post_view(post),
        "matches_created": len(new_matches),
        "notifications_created": len(new_matches),
        "matches": [lead_service.to_response(m) for m in new_matches],
    }


def delete_post(post_id: int) -> None:
    _get(post_id)
    matching_service.remove_matches_for_post(post_id)
    del storage.posts[post_id]
