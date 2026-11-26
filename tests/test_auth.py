"""Registration, login and JWT tokens."""

import jwt
from sqlalchemy import select

from app.config import JWT_ALGORITHM, SECRET_KEY
from app.models import User
from tests.conftest import PASSWORD

REGISTER = {"email": "anna@example.com", "username": "anna", "password": PASSWORD}


# --- registration ----------------------------------------------------------


def test_register(anon_client):
    response = anon_client.post("/auth/register", json=REGISTER)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "anna@example.com"
    assert body["username"] == "anna"
    assert body["role"] == "user"
    assert "password" not in body and "hashed_password" not in body


def test_password_is_stored_as_hash(anon_client, test_session):
    anon_client.post("/auth/register", json=REGISTER)

    with test_session() as db:
        user = db.scalar(select(User).where(User.username == "anna"))
    assert user.hashed_password != PASSWORD
    assert user.hashed_password.startswith("$2")  # bcrypt hash


def test_register_duplicate_email(anon_client):
    anon_client.post("/auth/register", json=REGISTER)

    other = {**REGISTER, "username": "other", "email": "ANNA@example.com"}  # case ignored
    response = anon_client.post("/auth/register", json=other)

    assert response.status_code == 409
    assert "email" in response.json()["detail"]


def test_register_duplicate_username(anon_client):
    anon_client.post("/auth/register", json=REGISTER)

    other = {**REGISTER, "email": "other@example.com"}
    response = anon_client.post("/auth/register", json=other)

    assert response.status_code == 409
    assert "username" in response.json()["detail"]


def test_register_validation(anon_client):
    bad_email = {**REGISTER, "email": "not-an-email"}
    short_password = {**REGISTER, "password": "short"}
    bad_username = {**REGISTER, "username": "a b"}

    for payload in (bad_email, short_password, bad_username):
        assert anon_client.post("/auth/register", json=payload).status_code == 422
    assert anon_client.post("/auth/register", json={}).status_code == 422


def test_register_cannot_choose_role(anon_client):
    response = anon_client.post("/auth/register", json={**REGISTER, "role": "admin"})

    assert response.status_code == 201
    assert response.json()["role"] == "user"


# --- login -----------------------------------------------------------------


def test_login_with_username_and_with_email(anon_client):
    anon_client.post("/auth/register", json=REGISTER)

    by_username = anon_client.post("/auth/login", data={"username": "anna", "password": PASSWORD})
    by_email = anon_client.post(
        "/auth/login", data={"username": "anna@example.com", "password": PASSWORD}
    )

    for response in (by_username, by_email):
        assert response.status_code == 200
        assert response.json()["token_type"] == "bearer"
        assert response.json()["access_token"]


def test_login_wrong_password(anon_client):
    anon_client.post("/auth/register", json=REGISTER)

    response = anon_client.post("/auth/login", data={"username": "anna", "password": "wrong-pass"})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_login_unknown_user(anon_client):
    response = anon_client.post("/auth/login", data={"username": "nobody", "password": PASSWORD})

    assert response.status_code == 401
    # Same message as for a wrong password: do not reveal which part was wrong.
    assert response.json()["detail"] == "Incorrect email/username or password"


# --- tokens ----------------------------------------------------------------


def _token_for(anon_client) -> str:
    anon_client.post("/auth/register", json=REGISTER)
    login = anon_client.post("/auth/login", data={"username": "anna", "password": PASSWORD})
    return login.json()["access_token"]


def test_me_with_valid_token(anon_client):
    token = _token_for(anon_client)

    response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 200
    assert response.json()["username"] == "anna"


def test_protected_endpoint_without_token(anon_client):
    for path in ("/auth/me", "/api/trackers", "/api/posts", "/api/matches",
                 "/api/notifications", "/api/stats"):
        response = anon_client.get(path)
        assert response.status_code == 401, path
        assert response.headers["www-authenticate"] == "Bearer"


def test_protected_endpoint_with_invalid_token(anon_client):
    response = anon_client.get("/api/trackers", headers={"Authorization": "Bearer garbage"})

    assert response.status_code == 401


def test_token_signed_with_other_key_is_rejected(anon_client):
    anon_client.post("/auth/register", json=REGISTER)
    fake = jwt.encode({"sub": "1"}, "some-other-secret", algorithm=JWT_ALGORITHM)

    response = anon_client.get("/api/trackers", headers={"Authorization": f"Bearer {fake}"})

    assert response.status_code == 401


def test_expired_token_is_rejected(anon_client):
    anon_client.post("/auth/register", json=REGISTER)
    expired = jwt.encode({"sub": "1", "exp": 1}, SECRET_KEY, algorithm=JWT_ALGORITHM)

    response = anon_client.get("/api/trackers", headers={"Authorization": f"Bearer {expired}"})

    assert response.status_code == 401


def test_token_of_missing_user_is_rejected(anon_client):
    ghost = jwt.encode({"sub": "999"}, SECRET_KEY, algorithm=JWT_ALGORITHM)

    response = anon_client.get("/api/trackers", headers={"Authorization": f"Bearer {ghost}"})

    assert response.status_code == 401


def test_public_endpoints_need_no_token(anon_client):
    assert anon_client.get("/health").status_code == 200
    assert anon_client.get("/").status_code == 200
