"""Ensure /api/test/reset is gated behind APP_ENV=test."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app, current_app_env
from tests.support.api_client import ApiClient


@pytest.mark.api
@pytest.mark.smoke
def test_reset_available_in_test_env(api_client: ApiClient):
    assert current_app_env() == "test"
    response = api_client.reset_data()
    assert response.status_code == 200
    assert response.json()["status"] == "reset"


@pytest.mark.api
def test_reset_returns_404_when_not_test_env(monkeypatch: pytest.MonkeyPatch, isolated_db):
    _ = isolated_db
    monkeypatch.setenv("APP_ENV", "production")
    assert current_app_env() == "production"

    with TestClient(app) as client:
        response = client.post("/api/test/reset")
    assert response.status_code == 404

    # Restore for other fixtures (process-wide).
    monkeypatch.setenv("APP_ENV", "test")


@pytest.mark.api
def test_reset_restores_seed_data(alice_client: ApiClient, api_client: ApiClient):
    task_id = alice_client.create_task(title="Will be wiped").json()["id"]
    assert alice_client.get_task(task_id).status_code == 200

    reset = api_client.reset_data()
    assert reset.status_code == 200

    # After reset, previous tokens are cleared — re-authenticate.
    alice = api_client.as_user("alice")
    assert alice.get_task(task_id).status_code == 404
    assert {t["id"] for t in alice.list_tasks().json()["items"]} == {"task-1", "task-2"}
