from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.schemas.common import Platform, PostSource


class PostCreate(BaseModel):
    platform: Platform
    external_id: str = Field(
        max_length=100,
        description="Id of the post on its platform. Unique together with platform.",
    )
    author: str = Field(max_length=100)
    text: str = Field(max_length=2000)
    url: HttpUrl

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "platform": "bluesky",
                "external_id": "post-001",
                "author": "anna.bsky.social",
                "text": "Всем привет! Мне НУЖЕН САЙТ для магазина",
                "url": "https://bsky.app/profile/anna.bsky.social/post/post-001",
            }
        }
    )

    @field_validator("external_id", "author", "text")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Field cannot be empty")
        return value


class PostResponse(BaseModel):
    id: int
    platform: Platform
    external_id: str
    author: str
    text: str
    url: str
    source: PostSource = Field(
        description="'demo' marks test data, 'manual' marks posts added via the API"
    )
    match_count: int = Field(description="Number of trackers this post matched")
    created_at: datetime
