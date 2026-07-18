"""Test data factories with unique values per call."""

from __future__ import annotations

import itertools
import uuid
from typing import Any

_counter = itertools.count(1)


def unique_suffix() -> str:
    return f"{next(_counter)}-{uuid.uuid4().hex[:8]}"


def user_payload(
    *,
    username: str | None = None,
    password: str = "Passw0rd!",
    display_name: str | None = None,
) -> dict[str, str]:
    suffix = unique_suffix()
    return {
        "username": username or f"user_{suffix}",
        "password": password,
        "display_name": display_name or f"User {suffix}",
    }


def task_payload(
    *,
    title: str | None = None,
    description: str = "factory generated",
    status: str = "todo",
    priority: str = "medium",
    due_date: str | None = None,
) -> dict[str, Any]:
    suffix = unique_suffix()
    payload: dict[str, Any] = {
        "title": title or f"Task {suffix}",
        "description": description,
        "status": status,
        "priority": priority,
    }
    if due_date is not None:
        payload["due_date"] = due_date
    return payload
