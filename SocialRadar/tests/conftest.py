"""Shared test setup.

Tests run against a separate PostgreSQL database named like the main one
plus "_test" (for example `socialradar_test`). It is created automatically,
and every test starts with empty tables, so tests do not depend on each
other and the real data is never touched.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (registers the tables)
from app.config import DATABASE_URL
from app.database import Base, get_db
from app.main import app

_main_url = make_url(DATABASE_URL)
TEST_DB_NAME = f"{_main_url.database}_test"
TEST_URL = _main_url.set(database=TEST_DB_NAME)


def _ensure_test_database() -> None:
    admin = create_engine(_main_url, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(
            text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": TEST_DB_NAME}
        )
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{TEST_DB_NAME}"'))
    admin.dispose()


@pytest.fixture(scope="session")
def test_engine():
    _ensure_test_database()
    engine = create_engine(TEST_URL)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def clean_database(test_engine):
    """Empty every table (and restart the ids) before each test."""
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with test_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
    yield


@pytest.fixture
def client(test_engine) -> TestClient:
    TestSession = sessionmaker(bind=test_engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


# --- helpers used by several test files ------------------------------------


def tracker_payload(**overrides) -> dict:
    payload = {
        "name": "Website Leads",
        "keywords": ["нужен сайт", "ищу разработчика", "website developer"],
        "excluded_keywords": ["бесплатно", "стажировка"],
        "platforms": ["bluesky", "threads"],
        "is_active": True,
    }
    payload.update(overrides)
    return payload


def post_payload(**overrides) -> dict:
    payload = {
        "platform": "bluesky",
        "external_id": "post-001",
        "author": "anna.bsky.social",
        "text": "Всем привет! Мне НУЖЕН САЙТ для магазина",
        "url": "https://bsky.app/profile/anna.bsky.social/post/post-001",
    }
    payload.update(overrides)
    return payload


def create_tracker(client: TestClient, **overrides) -> dict:
    response = client.post("/api/trackers", json=tracker_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def create_post(client: TestClient, **overrides) -> dict:
    response = client.post("/api/posts", json=post_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()
