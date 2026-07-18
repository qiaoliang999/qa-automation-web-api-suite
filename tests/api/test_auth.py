"""API tests for authentication endpoints."""

from __future__ import annotations

import pytest

from tests.helpers.api_client import ApiClient
from tests.helpers.config import USERS


@pytest.mark.api
@pytest.mark.smoke
def test_health_endpoint(api_client: ApiClient):
    response = api_client.health()
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "tasktrack"


@pytest.mark.api
@pytest.mark.smoke
def test_login_success(api_client: ApiClient):
    user = USERS["alice"]
    response = api_client.login(user["username"], user["password"])
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    assert body["username"] == user["username"]
    assert body["display_name"] == user["display_name"]


@pytest.mark.api
def test_login_invalid_password(api_client: ApiClient):
    response = api_client.login("alice", "wrong-password")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"


@pytest.mark.api
def test_login_unknown_user(api_client: ApiClient):
    response = api_client.login("does-not-exist", "whatever")
    assert response.status_code == 401
    assert "Invalid username or password" in response.json()["detail"]


@pytest.mark.api
def test_me_requires_auth(api_client: ApiClient):
    response = api_client.me()
    assert response.status_code == 401


@pytest.mark.api
def test_me_with_valid_token(alice_client: ApiClient):
    response = alice_client.me()
    assert response.status_code == 200
    body = response.json()
    assert body["username"] == "alice"
    assert body["display_name"] == "Alice Anderson"
    assert body["id"] == "user-alice"


@pytest.mark.api
def test_register_new_user(api_client: ApiClient):
    response = api_client.register(
        username="charlie",
        password="charlie1",
        display_name="Charlie Chen",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "charlie"
    assert body["display_name"] == "Charlie Chen"
    assert body["access_token"]


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
def test_register_validation_errors(api_client: ApiClient):
    response = api_client.register(username="ab", password="1", display_name="")
    assert response.status_code == 422
