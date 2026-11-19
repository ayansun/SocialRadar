"""Database engine, session factory and the get_db dependency."""

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    """Parent class of all SQLAlchemy models."""


def get_db() -> Iterator[Session]:
    """One session per request. It is always closed, which rolls back
    anything that was not committed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
