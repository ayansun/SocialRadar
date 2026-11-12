from pydantic import BaseModel

from app.schemas.match import MatchResponse


class StatsResponse(BaseModel):
    trackers_total: int
    trackers_active: int
    posts_total: int
    matches_total: int
    notifications_unread: int
    recent_matches: list[MatchResponse]
