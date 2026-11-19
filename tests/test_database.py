"""Tests for database-level behaviour: relationships, constraints, cascades."""

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import Match, Notification, Post, Tracker
from tests.conftest import create_post, create_tracker, post_payload


@pytest.fixture
def db(test_engine):
    with Session(test_engine) as session:
        yield session


def _count(db: Session, model) -> int:
    return db.scalar(select(func.count()).select_from(model))


def test_one_tracker_has_many_matches(client, db):
    tracker = create_tracker(client)
    create_post(client, external_id="a")
    create_post(client, external_id="b")

    stored = db.get(Tracker, tracker["id"])
    assert len(stored.matches) == 2
    assert all(m.tracker_id == stored.id for m in stored.matches)


def test_one_post_has_many_matches(client, db):
    create_tracker(client, name="First")
    create_tracker(client, name="Second")
    created = create_post(client)

    stored = db.get(Post, created["post"]["id"])
    assert len(stored.matches) == 2


def test_deleting_tracker_cascades_to_matches_and_notifications(client, db):
    tracker = create_tracker(client)
    create_post(client)
    assert _count(db, Match) == 1 and _count(db, Notification) == 1

    assert client.delete(f"/api/trackers/{tracker['id']}").status_code == 204
    db.expire_all()
    assert _count(db, Match) == 0
    assert _count(db, Notification) == 0
    assert _count(db, Post) == 1  # the post itself stays


def test_deleting_post_cascades_to_matches_and_notifications(client, db):
    create_tracker(client)
    created = create_post(client)

    assert client.delete(f"/api/posts/{created['post']['id']}").status_code == 204
    db.expire_all()
    assert _count(db, Match) == 0
    assert _count(db, Notification) == 0
    assert _count(db, Tracker) == 1  # the tracker stays


def test_database_rejects_duplicate_post(db):
    row = dict(platform="bluesky", external_id="x", author="a", text="t", url="https://e.com")
    db.add(Post(**row))
    db.commit()
    db.add(Post(**row))
    with pytest.raises(IntegrityError):
        db.commit()


def test_database_rejects_invalid_status(client, db):
    create_tracker(client)
    create_post(client)
    match = db.scalars(select(Match)).one()
    match.status = "banana"
    with pytest.raises(IntegrityError):
        db.commit()


def test_database_rejects_match_for_missing_tracker(db):
    post = Post(platform="bluesky", external_id="y", author="a", text="t", url="https://e.com")
    db.add(post)
    db.commit()
    db.add(Match(tracker_id=999, post_id=post.id, matched_keywords=["x"]))
    with pytest.raises(IntegrityError):
        db.commit()


def test_tracker_name_is_unique_ignoring_case_in_database(client, db):
    create_tracker(client, name="Leads")
    db.add(Tracker(name="LEADS", keywords=["a"], excluded_keywords=[], platforms=["bluesky"]))
    with pytest.raises(IntegrityError):
        db.commit()


def test_data_is_stored_in_the_database(client, db):
    create_tracker(client)
    create_post(client)
    db.expire_all()
    assert _count(db, Tracker) == 1
    assert _count(db, Post) == 1
    assert _count(db, Match) == 1
    assert _count(db, Notification) == 1


def test_duplicate_post_returns_409_and_stores_nothing_extra(client, db):
    create_post(client)
    response = client.post("/api/posts", json=post_payload())
    assert response.status_code == 409
    db.expire_all()
    assert _count(db, Post) == 1
