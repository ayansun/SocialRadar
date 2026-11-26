from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, require_admin
from app.models import User
from app.api.responses import CONFLICT, NOT_FOUND
from app.schemas.common import Platform, PostSource
from app.schemas.match import PostIngestResponse
from app.schemas.post import PostCreate, PostResponse
from app.services import post_service

# Posts are shared by all users: any logged-in user can read and add them,
# only an admin can delete them (a deletion also removes other users' leads).
router = APIRouter(
    prefix="/api/posts", tags=["Posts"], dependencies=[Depends(get_current_user)]
)


@router.get("", response_model=list[PostResponse], summary="List posts")
def list_posts(
    platform: Platform | None = Query(default=None),
    source: PostSource | None = Query(default=None, description="demo or manual"),
    search: str | None = Query(default=None, description="Part of the text or author"),
    has_matches: bool | None = Query(default=None, description="Only posts with / without matches"),
    db: Session = Depends(get_db),
):
    return post_service.list_posts(db, platform, source, search, has_matches)


@router.post(
    "",
    response_model=PostIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a post and run keyword matching",
    description=(
        "Saves the post, checks it against every active tracker and creates "
        "a match and a notification for each tracker that fits."
    ),
    responses=CONFLICT,
)
def create_post(
    data: PostCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)
):
    return post_service.create_post(db, data, user=user)


@router.get(
    "/{post_id}", response_model=PostResponse, summary="Get one post", responses=NOT_FOUND
)
def get_post(post_id: int, db: Session = Depends(get_db)):
    return post_service.get_post(db, post_id)


@router.delete(
    "/{post_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a post",
    description="Admin only. Also deletes the post's matches and their notifications.",
    responses=NOT_FOUND,
    dependencies=[Depends(require_admin)],
)
def delete_post(post_id: int, db: Session = Depends(get_db)):
    post_service.delete_post(db, post_id)
