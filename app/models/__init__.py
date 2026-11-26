"""Database models. Importing this package registers all tables on Base."""

from app.models.match import Match
from app.models.notification import Notification
from app.models.post import Post
from app.models.tracker import Tracker
from app.models.user import User

__all__ = ["Match", "Notification", "Post", "Tracker", "User"]
