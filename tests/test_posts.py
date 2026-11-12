"""Workflow 2: post ingestion."""

from tests.conftest import create_post, create_tracker, post_payload


def test_import_post(client):
    response = client.post("/api/posts", json=post_payload())

    assert response.status_code == 201
    body = response.json()
    assert body["post"]["id"] == 1
    assert body["post"]["platform"] == "bluesky"
    assert body["post"]["source"] == "manual"
    # No trackers exist yet, so nothing can match.
    assert body["matches_created"] == 0
    assert body["matches"] == []


def test_import_same_post_twice(client):
    create_post(client)

    response = client.post("/api/posts", json=post_payload())

    assert response.status_code == 409
    assert response.json() == {"detail": "Post already exists"}
    assert len(client.get("/api/posts").json()) == 1


def test_same_external_id_on_another_platform_is_allowed(client):
    create_post(client, platform="bluesky")

    response = client.post("/api/posts", json=post_payload(platform="threads"))

    assert response.status_code == 201


def test_import_post_with_invalid_data(client):
    assert client.post("/api/posts", json=post_payload(platform="twitter")).status_code == 422
    assert client.post("/api/posts", json=post_payload(text="   ")).status_code == 422
    assert client.post("/api/posts", json=post_payload(url="not a url")).status_code == 422
    assert client.get("/api/posts").json() == []


def test_get_post(client):
    post = create_post(client)["post"]

    response = client.get(f"/api/posts/{post['id']}")

    assert response.status_code == 200
    assert response.json()["author"] == "anna.bsky.social"


def test_get_missing_post(client):
    response = client.get("/api/posts/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Post not found"}


def test_delete_post_removes_its_matches_and_notifications(client):
    create_tracker(client)
    first = create_post(client)["post"]
    create_post(client, external_id="post-002", text="Ищу разработчика для проекта")
    assert len(client.get("/api/matches").json()) == 2

    response = client.delete(f"/api/posts/{first['id']}")

    assert response.status_code == 204
    matches = client.get("/api/matches").json()
    notifications = client.get("/api/notifications").json()
    assert len(matches) == 1 and matches[0]["post_id"] != first["id"]
    assert len(notifications) == 1 and notifications[0]["post_id"] != first["id"]
    # The tracker stays, with an updated match counter.
    assert client.get("/api/trackers/1").json()["match_count"] == 1


def test_delete_missing_post(client):
    assert client.delete("/api/posts/999").status_code == 404


def test_filter_posts(client):
    create_tracker(client)
    create_post(client)  # bluesky, matches
    create_post(
        client, platform="threads", external_id="t-1", author="oliver", text="Nice weather today"
    )

    threads = client.get("/api/posts", params={"platform": "threads"}).json()
    found = client.get("/api/posts", params={"search": "WEATHER"}).json()
    matched = client.get("/api/posts", params={"has_matches": True}).json()

    assert [p["author"] for p in threads] == ["oliver"]
    assert [p["author"] for p in found] == ["oliver"]
    assert [p["author"] for p in matched] == ["anna.bsky.social"]


def test_demo_seed(client):
    create_tracker(client)

    first = client.post("/api/demo/seed")
    second = client.post("/api/demo/seed")

    assert first.status_code == 200
    assert first.json()["imported"] == 10
    assert first.json()["matches_created"] > 0
    # Running it again adds nothing.
    assert second.json()["imported"] == 0
    assert second.json()["skipped"] == 10
    posts = client.get("/api/posts").json()
    assert len(posts) == 10
    # Demo posts are clearly marked as test data.
    assert all(p["source"] == "demo" for p in posts)
    assert client.get("/api/posts", params={"source": "manual"}).json() == []
