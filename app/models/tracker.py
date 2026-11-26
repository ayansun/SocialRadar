from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Index, String, func, true
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import created_at_column, utcnow


class Tracker(Base):
    """A saved search: keywords to look for on selected platforms."""

    __tablename__ = "trackers"
    __table_args__ = (
        CheckConstraint("jsonb_array_length(keywords) > 0", name="ck_trackers_keywords_not_empty"),
        CheckConstraint("jsonb_array_length(platforms) > 0", name="ck_trackers_platforms_not_empty"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    # The user who owns this tracker. NULL only for trackers created before
    # authentication existed; only an admin can see those.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    excluded_keywords: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    platforms: Mapped[list[str]] = mapped_column(JSONB, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default=true())
    created_at: Mapped[datetime] = created_at_column()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )

    # One tracker -> many matches. Deleting a tracker deletes its matches
    # (and, through them, their notifications).
    matches: Mapped[list["Match"]] = relationship(  # noqa: F821
        back_populates="tracker", cascade="all, delete-orphan", passive_deletes=True
    )


# Tracker names are unique, ignoring letter case.
Index("uq_trackers_name_lower", func.lower(Tracker.name), unique=True)
