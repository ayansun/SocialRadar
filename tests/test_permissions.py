"""Who may do what: ownership of trackers / leads / notifications and admin rights."""

from tests.conftest import create_post, create_tracker


def test_user_sees_only_own_trackers(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    create_tracker(alice, name="Alice tracker")
    create_tracker(bob, name="Bob tracker")

    names = [t["name"] for t in alice.get("/api/trackers").json()]

    assert names == ["Alice tracker"]


def test_user_cannot_read_other_users_tracker(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    tracker = create_tracker(alice)

    assert bob.get(f"/api/trackers/{tracker['id']}").status_code == 403


def test_user_cannot_modify_other_users_tracker(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    tracker = create_tracker(alice)

    response = bob.patch(f"/api/trackers/{tracker['id']}", json={"name": "Hacked"})

    assert response.status_code == 403
    assert alice.get(f"/api/trackers/{tracker['id']}").json()["name"] == "Website Leads"


def test_user_cannot_delete_other_users_tracker(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    tracker = create_tracker(alice)

    assert bob.delete(f"/api/trackers/{tracker['id']}").status_code == 403
    assert alice.get(f"/api/trackers/{tracker['id']}").status_code == 200


def test_owner_can_modify_and_delete_own_tracker(client):
    tracker = create_tracker(client)

    assert client.patch(f"/api/trackers/{tracker['id']}", json={"name": "New"}).status_code == 200
    assert client.delete(f"/api/trackers/{tracker['id']}").status_code == 204


def test_missing_tracker_is_still_404(client):
    assert client.get("/api/trackers/999").status_code == 404


def test_leads_and_notifications_are_private(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    create_tracker(alice)
    create_post(alice)  # matches Alice's tracker

    assert len(alice.get("/api/matches").json()) == 1
    assert len(alice.get("/api/notifications").json()) == 1
    # Bob has no trackers, so he sees nothing, although the post is shared.
    assert bob.get("/api/matches").json() == []
    assert bob.get("/api/notifications").json() == []
    assert bob.get("/api/stats").json()["matches_total"] == 0
    assert bob.get("/api/stats").json()["notifications_unread"] == 0
    assert bob.get("/api/matches", params={"tracker_id": 1}).status_code == 403


def test_user_cannot_touch_other_users_lead_or_notification(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    create_tracker(alice)
    create_post(alice)

    assert bob.get("/api/matches/1").status_code == 403
    assert bob.patch("/api/matches/1/status", json={"status": "saved"}).status_code == 403
    assert bob.patch("/api/notifications/1", json={"is_read": True}).status_code == 403
    assert bob.delete("/api/notifications/1").status_code == 403
    assert alice.get("/api/matches/1").json()["status"] == "new"


def test_new_post_response_shows_only_own_leads(make_client):
    alice, bob = make_client("alice"), make_client("bob")
    create_tracker(alice, name="Alice tracker")
    create_tracker(bob, name="Bob tracker")

    result = create_post(alice)

    assert result["matches_created"] == 1
    assert [m["tracker_name"] for m in result["matches"]] == ["Alice tracker"]
    # Both users get their own lead for the shared post.
    assert len(bob.get("/api/matches").json()) == 1


def test_regular_user_cannot_delete_posts_or_seed_demo(client, admin_client):
    post = create_post(client)["post"]

    assert client.delete(f"/api/posts/{post['id']}").status_code == 403
    assert client.post("/api/demo/seed").status_code == 403
    assert admin_client.post("/api/demo/seed").status_code == 200
    assert admin_client.delete(f"/api/posts/{post['id']}").status_code == 204


def test_admin_can_see_and_manage_all_trackers(make_client, admin_client):
    alice = make_client("alice")
    tracker = create_tracker(alice)

    assert [t["id"] for t in admin_client.get("/api/trackers").json()] == [tracker["id"]]
    assert admin_client.patch(f"/api/trackers/{tracker['id']}", json={"name": "By admin"}).status_code == 200
    assert admin_client.delete(f"/api/trackers/{tracker['id']}").status_code == 204


def test_admin_sees_all_leads(make_client, admin_client):
    alice = make_client("alice")
    create_tracker(alice)
    create_post(alice)

    assert len(admin_client.get("/api/matches").json()) == 1
    assert len(admin_client.get("/api/notifications").json()) == 1
