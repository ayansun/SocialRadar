"""Shared test setup.

Every test starts with empty in-memory storage, so tests do not depend on
each other and can run in any order.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.storage import storage


@pytest.fixture(autouse=True)
def clean_storage():
    storage.reset()
    yield
    storage.reset()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)




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
