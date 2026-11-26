from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import created_at_column, utcnow


class Match(Base):
    """A tracker found a post. This is a lead with a status."""

    __tablename__ = "matches"
    __table_args__ = (
        UniqueConstraint("tracker_id", "post_id", name="uq_matches_tracker_post"),
        CheckConstraint(
            "status IN ('new', 'saved', 'contacted', 'dismissed')", name="ck_matches_status"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    tracker_id: Mapped[int] = mapped_column(
        ForeignKey("trackers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    post_id: Mapped[int] = mapped_column(
        ForeignKey("posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    matched_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="new", server_default="new")
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    tracker: Mapped["Tracker"] = relationship(back_populates="matches")  # noqa: F821
    post: Mapped["Post"] = relationship(back_populates="matches")  # noqa: F821
    # One match -> many notifications (the app creates exactly one).
    notifications: Mapped[list["Notification"]] = relationship(  # noqa: F821
        back_populates="match", cascade="all, delete-orphan", passive_deletes=True
    )
