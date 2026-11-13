"""Workflow 1: tracker management."""

from tests.conftest import create_post, create_tracker, tracker_payload


def test_create_tracker(client):
    response = client.post("/api/trackers", json=tracker_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["id"] == 1
    assert body["name"] == "Website Leads"
    assert body["platforms"] == ["bluesky", "threads"]
    assert body["is_active"] is True
    assert body["match_count"] == 0


def test_create_tracker_normalizes_keywords(client):
    tracker = create_tracker(
        client, keywords=["  Нужен   Сайт ", "нужен сайт", "Website Developer"]
    )

    assert tracker["keywords"] == ["нужен сайт", "website developer"]


def test_create_tracker_with_empty_keywords(client):
    response = client.post("/api/trackers", json=tracker_payload(keywords=[]))

    assert response.status_code == 422
    assert "At least one keyword is required" in response.text


def test_create_tracker_with_blank_keyword(client):
    response = client.post("/api/trackers", json=tracker_payload(keywords=["site", "   "]))

    assert response.status_code == 422
    assert "Keywords cannot be empty" in response.text


def test_create_tracker_with_empty_name(client):
    response = client.post("/api/trackers", json=tracker_payload(name="   "))

    assert response.status_code == 422
    assert "Tracker name cannot be empty" in response.text


def test_create_tracker_with_too_long_name(client):
    response = client.post("/api/trackers", json=tracker_payload(name="x" * 81))

    assert response.status_code == 422


def test_create_tracker_without_platforms(client):
    response = client.post("/api/trackers", json=tracker_payload(platforms=[]))

    assert response.status_code == 422
    assert "At least one platform is required" in response.text


def test_create_tracker_with_unknown_platform(client):
    response = client.post("/api/trackers", json=tracker_payload(platforms=["twitter"]))

    assert response.status_code == 422


def test_create_tracker_with_keyword_that_is_also_excluded(client):
    response = client.post(
        "/api/trackers",
        json=tracker_payload(keywords=["сайт"], excluded_keywords=["Сайт"]),
    )

    assert response.status_code == 422
    assert "cannot also be an excluded keyword" in response.text


def test_create_tracker_with_duplicate_name(client):
    create_tracker(client)

    response = client.post("/api/trackers", json=tracker_payload(name="website leads"))

    assert response.status_code == 409
    assert response.json() == {"detail": "Tracker with this name already exists"}


def test_get_tracker(client):
    tracker = create_tracker(client)

    response = client.get(f"/api/trackers/{tracker['id']}")

    assert response.status_code == 200
    assert response.json()["name"] == "Website Leads"


def test_get_missing_tracker(client):
    response = client.get("/api/trackers/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Tracker not found"}


def test_update_tracker(client):
    tracker = create_tracker(client)

    response = client.patch(
        f"/api/trackers/{tracker['id']}",
        json={"name": "Site Leads", "platforms": ["threads"], "is_active": False},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Site Leads"
    assert body["platforms"] == ["threads"]
    assert body["is_active"] is False
    # Fields that were not sent stay the same.
    assert body["keywords"] == tracker["keywords"]


def test_update_tracker_with_empty_body(client):
    tracker = create_tracker(client)

    response = client.patch(f"/api/trackers/{tracker['id']}", json={})

    assert response.status_code == 422
    assert "At least one field must be provided" in response.text


def test_update_tracker_to_existing_name(client):
    create_tracker(client, name="First")
    second = create_tracker(client, name="Second")

    response = client.patch(f"/api/trackers/{second['id']}", json={"name": "First"})

    assert response.status_code == 409


def test_update_tracker_excluded_overlapping_stored_keywords(client):
    tracker = create_tracker(client, keywords=["сайт"], excluded_keywords=[])

    response = client.patch(
        f"/api/trackers/{tracker['id']}", json={"excluded_keywords": ["сайт"]}
    )

    assert response.status_code == 422
    assert "cannot also be an excluded keyword" in response.json()["detail"]


def test_update_missing_tracker(client):
    response = client.patch("/api/trackers/999", json={"name": "Anything"})

    assert response.status_code == 404


def test_delete_tracker(client):
    tracker = create_tracker(client)

    response = client.delete(f"/api/trackers/{tracker['id']}")

    assert response.status_code == 204
    assert client.get(f"/api/trackers/{tracker['id']}").status_code == 404
    assert client.get("/api/trackers").json() == []


def test_delete_missing_tracker(client):
    assert client.delete("/api/trackers/999").status_code == 404


def test_delete_tracker_removes_its_matches_and_notifications(client):
    tracker = create_tracker(client)
    other = create_tracker(client, name="Other", keywords=["магазина"], excluded_keywords=[])
    create_post(client)  # matches both trackers
    assert len(client.get("/api/matches").json()) == 2
    assert len(client.get("/api/notifications").json()) == 2

    client.delete(f"/api/trackers/{tracker['id']}")

    matches = client.get("/api/matches").json()
    notifications = client.get("/api/notifications").json()
    assert [m["tracker_id"] for m in matches] == [other["id"]]
    assert [n["tracker_id"] for n in notifications] == [other["id"]]
    assert len(client.get("/api/posts").json()) == 1


def test_filter_trackers(client):
    create_tracker(client, name="Sites", platforms=["bluesky"])
    create_tracker(client, name="Bots", platforms=["threads"], is_active=False)

    active = client.get("/api/trackers", params={"is_active": True}).json()
    threads = client.get("/api/trackers", params={"platform": "threads"}).json()
    found = client.get("/api/trackers", params={"search": "bot"}).json()

    assert [t["name"] for t in active] == ["Sites"]
    assert [t["name"] for t in threads] == ["Bots"]
    assert [t["name"] for t in found] == ["Bots"]
