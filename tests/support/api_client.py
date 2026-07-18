"""API client used by in-process API tests and UI setup helpers."""

from __future__ import annotations

from typing import Any

import httpx

from tests.support.config import USERS


class ApiClient:
    """Thin wrapper around an httpx-compatible client.

    Supports:
    - Starlette/FastAPI TestClient (in-process API tests)
    - Network httpx.Client (UI helper against live server)

    Each instance holds its own Authorization token so multi-user scenarios
    do not clobber each other.
    """

    def __init__(
        self,
        client: Any,
        *,
        token: str | None = None,
        owns_client: bool = False,
    ) -> None:
        self._client = client
        self.token = token
        self._owns_client = owns_client

    @classmethod
    def from_test_client(cls, test_client: Any) -> "ApiClient":
        return cls(test_client, owns_client=False)

    @classmethod
    def from_base_url(cls, base_url: str, timeout: float = 10.0) -> "ApiClient":
        client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout)
        return cls(client, owns_client=True)

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def clone(self) -> "ApiClient":
        """Return a sibling client sharing the same transport without the token."""
        return ApiClient(self._client, token=None, owns_client=False)

    def authorized(self, token: str) -> "ApiClient":
        return ApiClient(self._client, token=token, owns_client=False)

    def _headers(self, auth: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def reset_data(self) -> Any:
        return self._client.post("/api/test/reset")

    def health(self) -> Any:
        return self._client.get("/health")

    def openapi(self) -> Any:
        return self._client.get("/openapi.json")

    def register(
        self,
        username: str,
        password: str,
        display_name: str,
        *,
        set_token: bool = True,
    ) -> Any:
        response = self._client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": password,
                "display_name": display_name,
            },
            headers=self._headers(auth=False),
        )
        if set_token and response.status_code == 201:
            self.token = response.json()["access_token"]
        return response

    def login(
        self,
        username: str,
        password: str,
        *,
        set_token: bool = True,
    ) -> Any:
        response = self._client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers=self._headers(auth=False),
        )
        if set_token and response.status_code == 200:
            self.token = response.json()["access_token"]
        return response

    def login_as(self, user_key: str, *, set_token: bool = True) -> Any:
        user = USERS[user_key]
        return self.login(user["username"], user["password"], set_token=set_token)

    def as_user(self, user_key: str) -> "ApiClient":
        """Factory: return a new client authenticated as a seeded user."""
        sibling = self.clone()
        response = sibling.login_as(user_key)
        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to authenticate as {user_key}: "
                f"{response.status_code} {response.text}"
            )
        return sibling

    def me(self, auth: bool = True) -> Any:
        return self._client.get("/api/auth/me", headers=self._headers(auth=auth))

    def list_tasks(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        status: str | None = None,
        auth: bool = True,
    ) -> Any:
        params: dict[str, Any] = {}
        if page is not None:
            params["page"] = page
        if page_size is not None:
            params["page_size"] = page_size
        if status is not None:
            params["status"] = status
        return self._client.get(
            "/api/tasks",
            params=params or None,
            headers=self._headers(auth=auth),
        )

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
        priority: str = "medium",
        due_date: str | None = None,
        *,
        auth: bool = True,
    ) -> Any:
        payload: dict[str, Any] = {
            "title": title,
            "description": description,
            "status": status,
            "priority": priority,
        }
        if due_date is not None:
            payload["due_date"] = due_date
        return self._client.post(
            "/api/tasks",
            json=payload,
            headers=self._headers(auth=auth),
        )

    def get_task(self, task_id: str, *, auth: bool = True) -> Any:
        return self._client.get(
            f"/api/tasks/{task_id}",
            headers=self._headers(auth=auth),
        )

    def update_task(
        self,
        task_id: str,
        payload: dict[str, Any],
        *,
        auth: bool = True,
    ) -> Any:
        return self._client.put(
            f"/api/tasks/{task_id}",
            json=payload,
            headers=self._headers(auth=auth),
        )

    def delete_task(self, task_id: str, *, auth: bool = True) -> Any:
        return self._client.delete(
            f"/api/tasks/{task_id}",
            headers=self._headers(auth=auth),
        )
