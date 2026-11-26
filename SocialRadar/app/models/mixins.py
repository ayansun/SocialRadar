from datetime import datetime, timezone

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def created_at_column() -> Mapped[datetime]:
    return mapped_column(
        DateTime(timezone=True), default=utcnow, server_default=func.now(), nullable=False
    )
