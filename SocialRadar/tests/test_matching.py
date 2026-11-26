"""Workflow 2: keyword matching and re-evaluation."""

from tests.conftest import create_post, create_tracker


def test_keyword_match_is_case_insensitive(client):
    tracker = create_tracker(client)

    result = create_post(client, text="Всем привет! Мне НУЖЕН   САЙТ для магазина")

    assert result["matches_created"] == 1
    match = result["matches"][0]
    assert match["tracker_id"] == tracker["id"]
    assert match["tracker_name"] == "Website Leads"
    assert match["matched_keywords"] == ["нужен сайт"]
    assert match["status"] == "new"
    assert match["post"]["id"] == result["post"]["id"]


def test_no_match(client):
    create_tracker(client)

    result = create_post(client, text="Сегодня отличная погода")

    assert result["matches_created"] == 0
    assert client.get("/api/matches").json() == []
    assert client.get("/api/notifications").json() == []


def test_excluded_keyword_blocks_match(client):
    create_tracker(client)

    result = create_post(client, text="Нужен сайт, но БЕСПЛАТНО")

    assert result["matches_created"] == 0
    assert client.get("/api/matches").json() == []


def test_inactive_tracker_creates_no_matches(client):
    create_tracker(client, is_active=False)

    result = create_post(client)

    assert result["matches_created"] == 0
    assert client.get("/api/matches").json() == []
    assert client.get("/api/notifications").json() == []


def test_tracker_ignores_other_platforms(client):
    create_tracker(client, platforms=["threads"])

    result = create_post(client, platform="bluesky")

    assert result["matches_created"] == 0


def test_post_can_match_several_trackers(client):
    create_tracker(client, name="Sites")
    create_tracker(client, name="Shops", keywords=["магазин"], excluded_keywords=[])

    result = create_post(client)

    assert result["matches_created"] == 2
    assert {m["tracker_name"] for m in result["matches"]} == {"Sites", "Shops"}


def test_new_tracker_matches_stored_posts(client):
    create_post(client)

    tracker = create_tracker(client)

    assert tracker["match_count"] == 1
    assert len(client.get("/api/notifications").json()) == 1


def test_updating_keywords_removes_stale_matches(client):
    tracker = create_tracker(client)
    create_post(client)
    assert len(client.get("/api/matches").json()) == 1

    client.patch(f"/api/trackers/{tracker['id']}", json={"keywords": ["python"]})

    # The post no longer fits, so the match and its notification are gone.
    assert client.get("/api/matches").json() == []
    assert client.get("/api/notifications").json() == []


def test_updating_tracker_does_not_duplicate_matches(client):
    tracker = create_tracker(client)
    create_post(client)
    match = client.get("/api/matches").json()[0]
    client.patch(f"/api/matches/{match['id']}/status", json={"status": "saved"})

    # The post still fits after these edits.
    client.patch(f"/api/trackers/{tracker['id']}", json={"name": "Renamed"})
    client.patch(
        f"/api/trackers/{tracker['id']}", json={"keywords": ["нужен сайт", "магазина"]}
    )

    matches = client.get("/api/matches").json()
    assert len(matches) == 1
    assert matches[0]["id"] == match["id"]
    assert matches[0]["status"] == "saved"  # lead status survives the edit
    assert matches[0]["tracker_name"] == "Renamed"
    assert matches[0]["matched_keywords"] == ["нужен сайт", "магазина"]
    assert len(client.get("/api/notifications").json()) == 1


def test_pausing_keeps_matches_and_activating_rescans(client):
    tracker = create_tracker(client)
    create_post(client)

    client.patch(f"/api/trackers/{tracker['id']}", json={"is_active": False})
    # Existing matches stay, but a new post is ignored while paused.
    create_post(client, external_id="post-002", text="Ищу разработчика")
    assert len(client.get("/api/matches").json()) == 1

    client.patch(f"/api/trackers/{tracker['id']}", json={"is_active": True})

    # Stored posts are re-checked when the tracker is turned on again.
    assert len(client.get("/api/matches").json()) == 2
    assert len(client.get("/api/notifications").json()) == 2


def test_filter_matches(client):
    sites = create_tracker(client, name="Sites")
    create_tracker(client, name="Bots", keywords=["бот"], excluded_keywords=[])
    create_post(client)  # bluesky -> Sites
    create_post(client, platform="threads", external_id="t-1", text="Нужен бот для заказов")
    first_id = client.get("/api/matches", params={"tracker_id": sites["id"]}).json()[0]["id"]
    client.patch(f"/api/matches/{first_id}/status", json={"status": "saved"})

    by_platform = client.get("/api/matches", params={"platform": "threads"}).json()
    by_tracker = client.get("/api/matches", params={"tracker_id": sites["id"]}).json()
    by_status = client.get("/api/matches", params={"status": "saved"}).json()
    by_search = client.get("/api/matches", params={"search": "заказов"}).json()
    combined = client.get(
        "/api/matches", params={"platform": "threads", "status": "saved"}
    ).json()

    assert [m["tracker_name"] for m in by_platform] == ["Bots"]
    assert [m["tracker_name"] for m in by_tracker] == ["Sites"]
    assert [m["id"] for m in by_status] == [first_id]
    assert [m["tracker_name"] for m in by_search] == ["Bots"]
    assert combined == []


def test_filter_matches_by_missing_tracker(client):
    response = client.get("/api/matches", params={"tracker_id": 999})

    assert response.status_code == 404
    assert response.json() == {"detail": "Tracker not found"}


def test_filter_matches_by_invalid_status(client):
    assert client.get("/api/matches", params={"status": "archived"}).status_code == 422
