from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.post import PostResponse


class NotificationResponse(BaseModel):
    id: int
    match_id: int
    tracker_id: int
    post_id: int
    message: str
    post: PostResponse
    is_read: bool
    created_at: datetime


class NotificationUpdate(BaseModel):
    is_read: bool

    model_config = ConfigDict(json_schema_extra={"example": {"is_read": True}})
