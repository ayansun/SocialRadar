from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.demo_data import DEMO_POSTS
from app.errors import ConflictError
from app.database import get_db
from app.dependencies import require_admin
from app.schemas.common import PostSource
from app.schemas.match import DemoSeedResponse
from app.schemas.post import PostCreate
from app.services import post_service

router = APIRouter(tags=["Other"], dependencies=[Depends(require_admin)])


@router.post(
    "/api/demo/seed",
    response_model=DemoSeedResponse,
    summary="Import demo posts (admin only)",
    description=(
        "Loads a prepared set of test posts (not real Bluesky / Threads "
        "posts) through the normal ingestion workflow. Posts that were "
        "already imported are skipped, so calling it twice is safe."
    ),
)
def seed_demo_posts(db: Session = Depends(get_db)):
    imported = 0
    skipped = 0
    matches_created = 0

    for item in DEMO_POSTS:
        try:
            result = post_service.create_post(db, PostCreate(**item), source=PostSource.DEMO)
        except ConflictError:
            skipped += 1
            continue
        imported += 1
        matches_created += result["matches_created"]

    return {
        "imported": imported,
        "skipped": skipped,
        "matches_created": matches_created,
        "message": f"Imported {imported} demo posts, skipped {skipped} already imported",
    }
