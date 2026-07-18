"""Thin API client used by API tests and as a setup helper for UI tests."""

from __future__ import annotations

from typing import Any

import httpx

from tests.helpers.config import BASE_URL, USERS


class ApiClient:
    def __init__(self, base_url: str = BASE_URL, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(base_url=self.base_url, timeout=timeout)
        self.token: str | None = None

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "ApiClient":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _headers(self, auth: bool = True) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def reset_data(self) -> httpx.Response:
        return self._client.post("/api/test/reset")

    def health(self) -> httpx.Response:
        return self._client.get("/health")

    def register(
        self,
        username: str,
        password: str,
        display_name: str,
    ) -> httpx.Response:
        return self._client.post(
            "/api/auth/register",
            json={
                "username": username,
                "password": password,
                "display_name": display_name,
            },
            headers=self._headers(auth=False),
        )

    def login(self, username: str, password: str) -> httpx.Response:
        response = self._client.post(
            "/api/auth/login",
            json={"username": username, "password": password},
            headers=self._headers(auth=False),
        )
        if response.status_code == 200:
            self.token = response.json()["access_token"]
        return response

    def login_as(self, user_key: str) -> httpx.Response:
        user = USERS[user_key]
        return self.login(user["username"], user["password"])

    def me(self) -> httpx.Response:
        return self._client.get("/api/auth/me", headers=self._headers())

    def list_tasks(self, auth: bool = True) -> httpx.Response:
        return self._client.get("/api/tasks", headers=self._headers(auth=auth))

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
        auth: bool = True,
    ) -> httpx.Response:
        return self._client.post(
            "/api/tasks",
            json={"title": title, "description": description, "status": status},
            headers=self._headers(auth=auth),
        )

    def get_task(self, task_id: str, auth: bool = True) -> httpx.Response:
        return self._client.get(
            f"/api/tasks/{task_id}",
            headers=self._headers(auth=auth),
        )

    def update_task(
        self,
        task_id: str,
        payload: dict[str, Any],
        auth: bool = True,
    ) -> httpx.Response:
        return self._client.put(
            f"/api/tasks/{task_id}",
            json=payload,
            headers=self._headers(auth=auth),
        )

    def delete_task(self, task_id: str, auth: bool = True) -> httpx.Response:
        return self._client.delete(
            f"/api/tasks/{task_id}",
            headers=self._headers(auth=auth),
        )
