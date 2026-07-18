"""Authorization matrix: owner vs peer vs admin across task operations."""

from __future__ import annotations

import pytest

from tests.support.api_client import ApiClient
from tests.support.config import ALL_SEED_TASK_IDS
from tests.support.factories import task_payload

# (actor, task_id, method, expected_status)
# task-1: alice, task-3: bob, task-4: admin
# Destructive success deletes are covered separately with freshly created tasks
# so the matrix stays non-destructive against seed fixtures.
AUTHZ_CASES = [
    # get
    ("alice", "task-1", "get", 200),
    ("alice", "task-3", "get", 403),
    ("alice", "task-4", "get", 403),
    ("bob", "task-3", "get", 200),
    ("bob", "task-1", "get", 403),
    ("admin", "task-1", "get", 200),
    ("admin", "task-3", "get", 200),
    ("admin", "task-4", "get", 200),
    # update
    ("alice", "task-1", "update", 200),
    ("alice", "task-3", "update", 403),
    ("bob", "task-1", "update", 403),
    ("bob", "task-3", "update", 200),
    ("admin", "task-1", "update", 200),
    ("admin", "task-3", "update", 200),
    # delete denials (success deletes use dedicated cases below)
    ("alice", "task-3", "delete", 403),
    ("bob", "task-1", "delete", 403),
]


@pytest.mark.api
@pytest.mark.authz
@pytest.mark.parametrize(
    "actor,task_id,method,expected",
    AUTHZ_CASES,
    ids=[f"{a}-{m}-{t}-{e}" for a, t, m, e in AUTHZ_CASES],
)
def test_task_authz_matrix(
    api_client: ApiClient,
    actor: str,
    task_id: str,
    method: str,
    expected: int,
):
    client = api_client.as_user(actor)
    if method == "get":
        response = client.get_task(task_id)
    elif method == "update":
        response = client.update_task(task_id, {"status": "done"})
    elif method == "delete":
        response = client.delete_task(task_id)
    else:  # pragma: no cover
        raise AssertionError(method)
    assert response.status_code == expected
    if expected == 403:
        assert response.json()["detail"] == "Forbidden"


@pytest.mark.api
@pytest.mark.authz
def test_owner_can_delete_own_task(alice_client: ApiClient):
    created = alice_client.create_task(**task_payload(title="owner-delete-target"))
    assert created.status_code == 201
    task_id = created.json()["id"]

    deleted = alice_client.delete_task(task_id)
    assert deleted.status_code == 204
    assert alice_client.get_task(task_id).status_code == 404


@pytest.mark.api
@pytest.mark.authz
def test_admin_can_delete_peer_task(api_client: ApiClient, admin_client: ApiClient):
    owner = api_client.as_user("bob")
    created = owner.create_task(**task_payload(title="admin-delete-target"))
    assert created.status_code == 201
    task_id = created.json()["id"]

    deleted = admin_client.delete_task(task_id)
    assert deleted.status_code == 204
    assert admin_client.get_task(task_id).status_code == 404


@pytest.mark.api
@pytest.mark.authz
@pytest.mark.smoke
def test_admin_lists_all_tasks(admin_client: ApiClient):
    response = admin_client.list_tasks()
    assert response.status_code == 200
    body = response.json()
    ids = {t["id"] for t in body["items"]}
    assert ids == ALL_SEED_TASK_IDS
    assert body["total"] == len(ALL_SEED_TASK_IDS)


@pytest.mark.api
@pytest.mark.authz
def test_user_cannot_list_others_tasks(alice_client: ApiClient, bob_client: ApiClient):
    alice_ids = {t["id"] for t in alice_client.list_tasks().json()["items"]}
    bob_ids = {t["id"] for t in bob_client.list_tasks().json()["items"]}
    assert "task-3" not in alice_ids
    assert "task-1" not in bob_ids
    assert "task-4" not in alice_ids


@pytest.mark.api
@pytest.mark.authz
@pytest.mark.parametrize(
    "endpoint",
    ["list", "create", "get", "update", "delete"],
)
def test_unauthenticated_matrix(api_client: ApiClient, endpoint: str):
    if endpoint == "list":
        response = api_client.list_tasks(auth=False)
    elif endpoint == "create":
        response = api_client.create_task(title="x", auth=False)
    elif endpoint == "get":
        response = api_client.get_task("task-1", auth=False)
    elif endpoint == "update":
        response = api_client.update_task("task-1", {"status": "done"}, auth=False)
    else:
        response = api_client.delete_task("task-1", auth=False)
    assert response.status_code == 401
    assert response.json()["detail"]


@pytest.mark.api
@pytest.mark.authz
def test_admin_status_filter_across_owners(admin_client: ApiClient):
    response = admin_client.list_tasks(status="todo")
    assert response.status_code == 200
    body = response.json()
    ids = {t["id"] for t in body["items"]}
    # seed: task-1 (alice todo), task-4 (admin todo)
    assert ids == {"task-1", "task-4"}
    assert all(t["status"] == "todo" for t in body["items"])


@pytest.mark.api
@pytest.mark.authz
def test_user_cannot_read_admin_owned_task(alice_client: ApiClient):
    """Peer users must not escalate into admin-owned seed work."""
    response = alice_client.get_task("task-4")
    assert response.status_code == 403
    assert response.json()["detail"] == "Forbidden"


@pytest.mark.api
@pytest.mark.authz
def test_owner_survives_peer_delete_attempt(
    alice_client: ApiClient,
    bob_client: ApiClient,
):
    """Failed peer deletes must leave the resource intact for the owner."""
    denied = bob_client.delete_task("task-1")
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Forbidden"

    still_there = alice_client.get_task("task-1")
    assert still_there.status_code == 200
    assert still_there.json()["id"] == "task-1"


@pytest.mark.api
@pytest.mark.authz
def test_invalid_token_is_rejected(api_client: ApiClient):
    forged = api_client.authorized("not-a-real-token")
    response = forged.list_tasks()
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
