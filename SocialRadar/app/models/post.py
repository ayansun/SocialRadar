from datetime import datetime

from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import created_at_column


class Post(Base):
    """A social media post that is checked against trackers."""

    __tablename__ = "posts"
    __table_args__ = (
        UniqueConstraint("platform", "external_id", name="uq_posts_platform_external_id"),
        CheckConstraint("platform IN ('bluesky', 'threads')", name="ck_posts_platform"),
        CheckConstraint("source IN ('manual', 'demo')", name="ck_posts_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(20), nullable=False)
    external_id: Mapped[str] = mapped_column(String(100), nullable=False)
    author: Mapped[str] = mapped_column(String(100), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str] = mapped_column(String(2083), nullable=False)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="manual")
    created_at: Mapped[datetime] = created_at_column()

    # One post -> many matches (one per matching tracker).
    matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="post", cascade="all, delete-orphan", passive_deletes=True
    )
