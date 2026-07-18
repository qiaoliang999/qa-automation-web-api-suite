"""Shared configuration for the TaskTrack automation suite."""

from __future__ import annotations

import os

# Base URL used only by UI tests against a live server process.
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Seeded users — must match app/database.py seed data.
USERS = {
    "alice": {
        "username": "alice",
        "password": "alice123",
        "display_name": "Alice Anderson",
        "id": "user-alice",
        "role": "user",
    },
    "bob": {
        "username": "bob",
        "password": "bob1234",
        "display_name": "Bob Baker",
        "id": "user-bob",
        "role": "user",
    },
    "admin": {
        "username": "admin",
        "password": "admin123",
        "display_name": "Admin User",
        "id": "user-admin",
        "role": "admin",
    },
}

ALICE_TASK_IDS = {"task-1", "task-2"}
BOB_TASK_IDS = {"task-3"}
ADMIN_TASK_IDS = {"task-4"}
ALL_SEED_TASK_IDS = ALICE_TASK_IDS | BOB_TASK_IDS | ADMIN_TASK_IDS

COOKIE_NAME = "tasktrack_token"
