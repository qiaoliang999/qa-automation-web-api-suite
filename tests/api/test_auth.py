"""API tests for authentication endpoints (in-process ASGI)."""

from __future__ import annotations

import pytest

from tests.support.api_client import ApiClient
from tests.support.config import USERS
from tests.support.factories import user_payload


@pytest.mark.api
@pytest.mark.smoke
def test_health_endpoint(api_client: ApiClient):
    response = api_client.health()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "tasktrack"
    assert body["version"] == "2.0.0"
    assert body["env"] == "test"


@pytest.mark.api
@pytest.mark.smoke
@pytest.mark.parametrize("user_key", ["alice", "bob", "admin"])
def test_login_success(api_client: ApiClient, user_key: str):
    user = USERS[user_key]
    response = api_client.login(user["username"], user["password"])
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["username"] == user["username"]
    assert body["display_name"] == user["display_name"]
    assert body["role"] == user["role"]


@pytest.mark.api
@pytest.mark.parametrize(
    "username,password",
    [
        ("alice", "wrong-password"),
        ("alice", ""),
        ("does-not-exist", "whatever"),
        ("admin", "alice123"),
    ],
)
def test_login_rejects_bad_credentials(api_client: ApiClient, username: str, password: str):
    response = api_client.login(username, password)
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.api
def test_me_requires_auth(api_client: ApiClient):
    response = api_client.me()
    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.parametrize("user_key", ["alice", "bob", "admin"])
def test_me_with_valid_token(api_client: ApiClient, user_key: str):
    client = api_client.as_user(user_key)
    response = client.me()
    assert response.status_code == 200
    body = response.json()
    user = USERS[user_key]
    assert body["username"] == user["username"]
    assert body["display_name"] == user["display_name"]
    assert body["id"] == user["id"]
    assert body["role"] == user["role"]


@pytest.mark.api
@pytest.mark.smoke
def test_register_new_user(api_client: ApiClient):
    payload = user_payload()
    response = api_client.register(**payload)
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == payload["username"]
    assert body["display_name"] == payload["display_name"]
    assert body["role"] == "user"
    assert body["access_token"]

    me = api_client.me()
    assert me.status_code == 200
    assert me.json()["username"] == payload["username"]


@pytest.mark.api
def test_register_duplicate_username(api_client: ApiClient):
    response = api_client.register(
        username="alice",
        password="newpass1",
        display_name="Alice Clone",
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Username already exists"


@pytest.mark.api
@pytest.mark.parametrize(
    "payload",
    [
        {"username": "ab", "password": "valid1", "display_name": "Ok"},
        {"username": "validuser", "password": "1", "display_name": "Ok"},
        {"username": "validuser", "password": "valid1", "display_name": ""},
        {"username": "   ", "password": "valid1", "display_name": "Ok"},
    ],
    ids=["short-username", "short-password", "empty-display", "whitespace-username"],
)
def test_register_validation_errors(api_client: ApiClient, payload: dict):
    response = api_client.register(**payload)
    assert response.status_code == 422


@pytest.mark.api
def test_passwords_are_hashed_not_plaintext(api_client: ApiClient):
    """Regression lock: store must not keep plaintext passwords."""
    from app.database import db

    user = db.find_user_by_username("alice")
    assert user is not None
    assert user.password_hash != "alice123"
    assert user.password_hash.startswith("pbkdf2_")


@pytest.mark.api
def test_tokens_are_opaque(api_client: ApiClient):
    response = api_client.login_as("alice")
    token = response.json()["access_token"]
    assert not token.startswith("tok-user-alice")
    assert len(token) >= 32
