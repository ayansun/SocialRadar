"""Workflow 3: notifications and dashboard stats."""

from tests.conftest import create_post, create_tracker


def test_match_creates_notification(client):
    tracker = create_tracker(client)

    result = create_post(client)

    assert result["notifications_created"] == 1
    notifications = client.get("/api/notifications").json()
    assert len(notifications) == 1
    notification = notifications[0]
    assert notification["is_read"] is False
    assert notification["tracker_id"] == tracker["id"]
    assert notification["match_id"] == result["matches"][0]["id"]
    assert notification["post"]["id"] == result["post"]["id"]
    assert notification["message"] == 'New lead for "Website Leads": anna.bsky.social on Bluesky'


def test_mark_notification_as_read(client):
    create_tracker(client)
    create_post(client)
    notification_id = client.get("/api/notifications").json()[0]["id"]

    response = client.patch(f"/api/notifications/{notification_id}", json={"is_read": True})

    assert response.status_code == 200
    assert response.json()["is_read"] is True


def test_filter_notifications_by_read_state(client):
    create_tracker(client)
    create_post(client)
    create_post(client, external_id="post-002", text="Ищу разработчика")
    first_id = client.get("/api/notifications").json()[-1]["id"]
    client.patch(f"/api/notifications/{first_id}", json={"is_read": True})

    unread = client.get("/api/notifications", params={"is_read": False}).json()
    read = client.get("/api/notifications", params={"is_read": True}).json()

    assert len(unread) == 1 and unread[0]["id"] != first_id
    assert [n["id"] for n in read] == [first_id]


def test_delete_notification_keeps_the_match(client):
    create_tracker(client)
    create_post(client)
    notification_id = client.get("/api/notifications").json()[0]["id"]

    response = client.delete(f"/api/notifications/{notification_id}")

    assert response.status_code == 204
    assert client.get("/api/notifications").json() == []
    assert len(client.get("/api/matches").json()) == 1


def test_missing_notification(client):
    patch = client.patch("/api/notifications/999", json={"is_read": True})
    delete = client.delete("/api/notifications/999")

    assert patch.status_code == 404
    assert patch.json() == {"detail": "Notification not found"}
    assert delete.status_code == 404


def test_stats(client):
    create_tracker(client)
    create_tracker(client, name="Paused", is_active=False)
    create_post(client)
    create_post(client, external_id="post-002", text="Nothing interesting")

    stats = client.get("/api/stats").json()

    assert stats["trackers_total"] == 2
    assert stats["trackers_active"] == 1
    assert stats["posts_total"] == 2
    assert stats["matches_total"] == 1
    assert stats["notifications_unread"] == 1
    assert len(stats["recent_matches"]) == 1


def test_health_and_frontend(client):
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/").status_code == 200
    assert "SocialRadar" in client.get("/").text
    assert client.get("/docs").status_code == 200
