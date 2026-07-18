"""API tests for task CRUD, filtering, pagination, and validation."""

from __future__ import annotations

import pytest

from tests.support.api_client import ApiClient
from tests.support.config import ALICE_TASK_IDS, BOB_TASK_IDS
from tests.support.factories import task_payload


@pytest.mark.api
@pytest.mark.smoke
def test_list_tasks_returns_owned_only(alice_client: ApiClient):
    response = alice_client.list_tasks()
    assert response.status_code == 200
    body = response.json()
    assert set(body.keys()) >= {"items", "total", "page", "page_size"}
    ids = {task["id"] for task in body["items"]}
    assert ids == ALICE_TASK_IDS
    assert body["total"] == 2
    assert all(task["owner_id"] == "user-alice" for task in body["items"])


@pytest.mark.api
def test_list_tasks_unauthorized(api_client: ApiClient):
    response = api_client.list_tasks(auth=False)
    assert response.status_code == 401


@pytest.mark.api
@pytest.mark.smoke
def test_create_task(alice_client: ApiClient):
    payload = task_payload(
        title="Automate smoke suite",
        description="Cover auth and CRUD",
        status="todo",
        priority="high",
        due_date="2026-12-01",
    )
    response = alice_client.create_task(**payload)
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == payload["title"]
    assert body["description"] == payload["description"]
    assert body["status"] == "todo"
    assert body["priority"] == "high"
    assert body["due_date"] == "2026-12-01"
    assert body["owner_id"] == "user-alice"
    assert body["id"]

    listed = alice_client.list_tasks().json()
    assert any(t["id"] == body["id"] for t in listed["items"])


@pytest.mark.api
@pytest.mark.parametrize(
    "title,expected_status",
    [
        ("   ", 422),
        ("", 422),
        ("x" * 121, 422),
        ("  Valid after strip  ", 201),
    ],
    ids=["whitespace", "empty", "too-long", "strip-ok"],
)
def test_create_task_title_validation(alice_client: ApiClient, title: str, expected_status: int):
    response = alice_client.create_task(title=title)
    assert response.status_code == expected_status
    if expected_status == 201:
        assert response.json()["title"] == "Valid after strip"


@pytest.mark.api
@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "blocked"),
        ("status", "TODO"),
        ("priority", "urgent"),
        ("priority", "MEDIUM"),
        ("due_date", "not-a-date"),
        ("due_date", "01-01-2026"),
    ],
    ids=["bad-status", "case-status", "bad-priority", "case-priority", "bad-date", "wrong-date-fmt"],
)
def test_create_task_invalid_fields(alice_client: ApiClient, field: str, value: str):
    kwargs = {"title": "ok", field: value}
    response = alice_client.create_task(**kwargs)
    assert response.status_code == 422


@pytest.mark.api
def test_create_task_missing_auth(api_client: ApiClient):
    response = api_client.create_task(title="No auth", auth=False)
    assert response.status_code == 401


@pytest.mark.api
def test_get_task_success(alice_client: ApiClient):
    response = alice_client.get_task("task-1")
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == "task-1"
    assert body["title"] == "Write test plan"
    assert body["priority"] == "high"
    assert body["due_date"] == "2026-08-01"


@pytest.mark.api
def test_get_task_not_found(alice_client: ApiClient):
    response = alice_client.get_task("missing-task")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


@pytest.mark.api
def test_update_task(alice_client: ApiClient):
    response = alice_client.update_task(
        "task-1",
        {
            "title": "Write updated test plan",
            "status": "done",
            "priority": "low",
            "due_date": "2026-10-10",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Write updated test plan"
    assert body["status"] == "done"
    assert body["priority"] == "low"
    assert body["due_date"] == "2026-10-10"

    fetched = alice_client.get_task("task-1").json()
    assert fetched["title"] == "Write updated test plan"
    assert fetched["status"] == "done"


@pytest.mark.api
def test_update_task_empty_title(alice_client: ApiClient):
    response = alice_client.update_task("task-1", {"title": "  "})
    assert response.status_code == 422


@pytest.mark.api
def test_delete_task(alice_client: ApiClient):
    create = alice_client.create_task(**task_payload(title="Temporary task"))
    assert create.status_code == 201
    task_id = create.json()["id"]

    delete = alice_client.delete_task(task_id)
    assert delete.status_code == 204
    assert delete.content == b""
    assert alice_client.get_task(task_id).status_code == 404


@pytest.mark.api
def test_delete_task_not_found(alice_client: ApiClient):
    response = alice_client.delete_task("no-such-task")
    assert response.status_code == 404


@pytest.mark.api
def test_bob_sees_only_own_tasks(bob_client: ApiClient):
    tasks = bob_client.list_tasks().json()
    assert {t["id"] for t in tasks["items"]} == BOB_TASK_IDS
    assert tasks["total"] == 1
    assert all(t["owner_id"] == "user-bob" for t in tasks["items"])


@pytest.mark.api
@pytest.mark.regression
def test_full_crud_lifecycle(alice_client: ApiClient):
    created = alice_client.create_task(**task_payload(title="Lifecycle task", status="todo"))
    assert created.status_code == 201
    task_id = created.json()["id"]

    read = alice_client.get_task(task_id)
    assert read.status_code == 200
    assert read.json()["title"] == "Lifecycle task"

    updated = alice_client.update_task(
        task_id,
        {"description": "updated", "status": "in_progress", "priority": "high"},
    )
    assert updated.status_code == 200
    assert updated.json()["status"] == "in_progress"
    assert updated.json()["priority"] == "high"

    deleted = alice_client.delete_task(task_id)
    assert deleted.status_code == 204
    assert alice_client.get_task(task_id).status_code == 404


@pytest.mark.api
@pytest.mark.parametrize(
    "status_filter,expected_ids",
    [
        ("todo", {"task-1"}),
        ("in_progress", {"task-2"}),
        ("done", set()),
    ],
)
def test_list_tasks_status_filter(
    alice_client: ApiClient,
    status_filter: str,
    expected_ids: set[str],
):
    response = alice_client.list_tasks(status=status_filter)
    assert response.status_code == 200
    body = response.json()
    assert {t["id"] for t in body["items"]} == expected_ids
    assert body["total"] == len(expected_ids)
    assert all(t["status"] == status_filter for t in body["items"])


@pytest.mark.api
def test_list_tasks_invalid_status_filter(alice_client: ApiClient):
    response = alice_client.list_tasks(status="blocked")
    assert response.status_code == 422


@pytest.mark.api
def test_list_tasks_pagination(alice_client: ApiClient):
    # Seed already has 2; add more for paging.
    for i in range(5):
        assert alice_client.create_task(title=f"Page task {i}").status_code == 201

    page1 = alice_client.list_tasks(page=1, page_size=3).json()
    page2 = alice_client.list_tasks(page=2, page_size=3).json()
    assert page1["page"] == 1
    assert page1["page_size"] == 3
    assert page1["total"] == 7
    assert len(page1["items"]) == 3
    assert page2["page"] == 2
    assert len(page2["items"]) == 3
    page1_ids = {t["id"] for t in page1["items"]}
    page2_ids = {t["id"] for t in page2["items"]}
    assert page1_ids.isdisjoint(page2_ids)

    page3 = alice_client.list_tasks(page=3, page_size=3).json()
    assert len(page3["items"]) == 1


@pytest.mark.api
@pytest.mark.parametrize(
    "page,page_size",
    [(0, 10), (-1, 10), (1, 0), (1, 101)],
)
def test_list_tasks_pagination_bounds(alice_client: ApiClient, page: int, page_size: int):
    response = alice_client.list_tasks(page=page, page_size=page_size)
    assert response.status_code == 422


@pytest.mark.api
def test_multi_user_clients_do_not_clobber(api_client: ApiClient):
    alice = api_client.as_user("alice")
    bob = api_client.as_user("bob")
    assert alice.token != bob.token
    alice_ids = {t["id"] for t in alice.list_tasks().json()["items"]}
    bob_ids = {t["id"] for t in bob.list_tasks().json()["items"]}
    assert alice_ids == ALICE_TASK_IDS
    assert bob_ids == BOB_TASK_IDS
