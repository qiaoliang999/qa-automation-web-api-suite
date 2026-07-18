"""API tests for task CRUD, ownership, and validation."""

from __future__ import annotations

import pytest

from tests.helpers.api_client import ApiClient
from tests.helpers.config import ALICE_TASK_IDS, USERS


@pytest.mark.api
@pytest.mark.smoke
def test_list_tasks_returns_owned_only(alice_client: ApiClient):
    response = alice_client.list_tasks()
    assert response.status_code == 200
    tasks = response.json()
    assert isinstance(tasks, list)
    ids = {task["id"] for task in tasks}
    assert ids == ALICE_TASK_IDS
    assert all(task["owner_id"] == "user-alice" for task in tasks)


@pytest.mark.api
def test_list_tasks_unauthorized(api_client: ApiClient):
    response = api_client.list_tasks(auth=False)
    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.smoke
def test_create_task(alice_client: ApiClient):
    response = alice_client.create_task(
        title="Automate smoke suite",
        description="Cover auth and CRUD",
        status="todo",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Automate smoke suite"
    assert body["description"] == "Cover auth and CRUD"
    assert body["status"] == "todo"
    assert body["owner_id"] == "user-alice"
    assert body["id"]

    listed = alice_client.list_tasks().json()
    assert any(t["id"] == body["id"] for t in listed)


@pytest.mark.api
def test_create_task_empty_title(alice_client: ApiClient):
    response = alice_client.create_task(title="   ")
    # FastAPI/Pydantic min_length or our strip check both yield 422.
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_missing_auth(api_client: ApiClient):
    response = api_client.create_task(title="No auth", auth=False)
    assert response.status_code == 401


@pytest.mark.api
def test_create_task_invalid_status(alice_client: ApiClient):
    response = alice_client.create_task(title="Bad status", status="blocked")
    assert response.status_code == 422


@pytest.mark.api
def test_get_task_success(alice_client: ApiClient):
    response = alice_client.get_task("task-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "task-1"
    assert body["title"] == "Write test plan"


@pytest.mark.api
def test_get_task_not_found(alice_client: ApiClient):
    response = alice_client.get_task("missing-task")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.api
def test_get_other_users_task_forbidden(api_client: ApiClient):
    login = api_client.login_as("alice")
    assert login.status_code == 200
    response = api_client.get_task("task-3")  # bob's task
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.api
def test_update_task(alice_client: ApiClient):
    response = alice_client.update_task(
        "task-1",
        {"title": "Write updated test plan", "status": "done"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Write updated test plan"
    assert body["status"] == "done"

    fetched = alice_client.get_task("task-1").json()
    assert fetched["title"] == "Write updated test plan"
    assert fetched["status"] == "done"


@pytest.mark.api
def test_update_task_empty_title(alice_client: ApiClient):
    response = alice_client.update_task("task-1", {"title": "  "})
    assert response.status_code == 422


@pytest.mark.api
def test_update_other_users_task_forbidden(api_client: ApiClient):
    login = api_client.login_as("alice")
    assert login.status_code == 200
    response = api_client.update_task("task-3", {"status": "done"})
    assert response.status_code == 403


@pytest.mark.api
def test_delete_task(alice_client: ApiClient):
    create = alice_client.create_task(title="Temporary task")
    assert create.status_code == 201
    task_id = create.json()["id"]

    delete = alice_client.delete_task(task_id)
    assert delete.status_code == 204
    assert delete.content == b""

    get_response = alice_client.get_task(task_id)
    assert get_response.status_code == 404


@pytest.mark.api
def test_delete_task_not_found(alice_client: ApiClient):
    response = alice_client.delete_task("no-such-task")
    assert response.status_code == 404


@pytest.mark.api
def test_delete_other_users_task_forbidden(api_client: ApiClient):
    login = api_client.login_as("alice")
    assert login.status_code == 200
    response = api_client.delete_task("task-3")
    assert response.status_code == 403


@pytest.mark.api
def test_bob_sees_only_own_tasks(api_client: ApiClient):
    login = api_client.login_as("bob")
    assert login.status_code == 200
    tasks = api_client.list_tasks().json()
    assert {t["id"] for t in tasks} == {"task-3"}
    assert all(t["owner_id"] == USERS["bob"]["id"] for t in tasks)


@pytest.mark.api
def test_full_crud_lifecycle(alice_client: ApiClient):
    """Regression-style happy path covering create → read → update → delete."""
    created = alice_client.create_task(
        title="Lifecycle task",
        description="end to end",
        status="todo",
    )
    assert created.status_code == 201
    task_id = created.json()["id"]

    read = alice_client.get_task(task_id)
    assert read.status_code == 200
    assert read.json()["title"] == "Lifecycle task"

    updated = alice_client.update_task(
        task_id,
        {"description": "updated", "status": "in_progress"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["description"] == "updated"

    deleted = alice_client.delete_task(task_id)
    assert deleted.status_code == 204
    assert alice_client.get_task(task_id).status_code == 404
