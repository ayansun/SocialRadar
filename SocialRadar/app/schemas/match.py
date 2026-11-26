from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import LeadStatus
from app.schemas.post import PostResponse


class MatchResponse(BaseModel):
    """A match between a tracker and a post. Each match is a potential lead."""

    id: int
    tracker_id: int
    tracker_name: str
    post_id: int
    post: PostResponse
    matched_keywords: list[str]
    status: LeadStatus
    allowed_statuses: list[LeadStatus] = Field(
        description="Statuses this lead can be moved to from its current status"
    )
    created_at: datetime
    updated_at: datetime


class MatchStatusUpdate(BaseModel):
    status: LeadStatus

    model_config = ConfigDict(json_schema_extra={"example": {"status": "saved"}})


class PostIngestResponse(BaseModel):
    """Result of adding a post: the post plus everything it triggered."""

    post: PostResponse
    matches_created: int
    notifications_created: int
    matches: list[MatchResponse]


class DemoSeedResponse(BaseModel):
    imported: int
    skipped: int = Field(description="Demo posts that were already imported")
    matches_created: int
    message: str
