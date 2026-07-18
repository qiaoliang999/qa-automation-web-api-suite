"""Test data factories with unique values per call.

Factories return plain dicts suitable for ``**kwargs`` expansion into
``ApiClient`` helpers or raw JSON bodies. Every generated username/title
includes a monotonic counter plus a short UUID fragment so parallel or
repeated calls never collide on uniqueness constraints.
"""

from __future__ import annotations

import itertools
import uuid
from typing import Any

_counter = itertools.count(1)


def unique_suffix() -> str:
    """Return a short unique token safe for usernames and titles."""
    return f"{next(_counter)}-{uuid.uuid4().hex[:8]}"


def user_payload(
    *,
    username: str | None = None,
    password: str = "Passw0rd!",
    display_name: str | None = None,
) -> dict[str, str]:
    """Build a valid registration body; override fields as needed."""
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
    """Build a valid task create body.

    ``due_date`` is omitted when ``None`` so callers can exercise the
    optional-field default path without sending an explicit null.
    """
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


def task_update_payload(**fields: Any) -> dict[str, Any]:
    """Build a partial task update body (only explicitly provided keys).

    Example::

        task_update_payload(status="done", priority="high")
    """
    allowed = {"title", "description", "status", "priority", "due_date"}
    unknown = set(fields) - allowed
    if unknown:
        raise ValueError(f"Unsupported task update fields: {sorted(unknown)}")
    return dict(fields)
