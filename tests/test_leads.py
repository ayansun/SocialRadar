"""Workflow 3: lead status processing."""

import pytest

from tests.conftest import create_post, create_tracker


@pytest.fixture
def match(client) -> dict:
    """One match with status "new"."""
    create_tracker(client)
    return create_post(client)["matches"][0]


def set_status(client, match_id: int, status: str):
    return client.patch(f"/api/matches/{match_id}/status", json={"status": status})


def test_get_match(client, match):
    response = client.get(f"/api/matches/{match['id']}")

    assert response.status_code == 200
    assert response.json()["status"] == "new"
    assert response.json()["allowed_statuses"] == ["saved", "dismissed"]


def test_get_missing_match(client):
    response = client.get("/api/matches/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Match not found"}


def test_change_lead_status(client, match):
    saved = set_status(client, match["id"], "saved")
    contacted = set_status(client, match["id"], "contacted")

    assert saved.status_code == 200
    assert saved.json()["status"] == "saved"
    assert contacted.status_code == 200
    assert contacted.json()["status"] == "contacted"
    assert client.get(f"/api/matches/{match['id']}").json()["status"] == "contacted"


def test_dismissed_lead_cannot_be_contacted_directly(client, match):
    set_status(client, match["id"], "dismissed")

    response = set_status(client, match["id"], "contacted")

    assert response.status_code == 409
    assert "Invalid lead status transition" in response.json()["detail"]
    assert client.get(f"/api/matches/{match['id']}").json()["status"] == "dismissed"


def test_new_lead_cannot_skip_to_contacted(client, match):
    assert set_status(client, match["id"], "contacted").status_code == 409


def test_dismissed_lead_can_be_restored(client, match):
    set_status(client, match["id"], "dismissed")

    response = set_status(client, match["id"], "new")

    assert response.status_code == 200
    assert response.json()["status"] == "new"


def test_unknown_status_is_rejected(client, match):
    response = set_status(client, match["id"], "archived")

    assert response.status_code == 422


def test_change_status_of_missing_match(client):
    assert set_status(client, 999, "saved").status_code == 404


def test_repeating_a_status_changes_nothing(client, match):
    first = set_status(client, match["id"], "saved").json()
    second = set_status(client, match["id"], "saved")

    assert second.status_code == 200
    assert second.json()["updated_at"] == first["updated_at"]
    # Status changes never create notifications.
    assert len(client.get("/api/notifications").json()) == 1
