from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.mixins import created_at_column


class Notification(Base):
    """Created automatically for every new match."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    match_id: Mapped[int] = mapped_column(
        ForeignKey("matches.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_read: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    created_at: Mapped[datetime] = created_at_column()

    match: Mapped["Match"] = relationship(back_populates="notifications")  # noqa: F821
