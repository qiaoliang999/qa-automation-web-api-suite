"""Shared configuration for the TaskTrack automation suite."""

from __future__ import annotations

import os

# Base URL of the running TaskTrack application under test.
BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")

# Seeded users — must match app/database.py seed data.
USERS = {
    "alice": {
        "username": "alice",
        "password": "alice123",
        "display_name": "Alice Anderson",
        "id": "user-alice",
    },
    "bob": {
        "username": "bob",
        "password": "bob1234",
        "display_name": "Bob Baker",
        "id": "user-bob",
    },
}

# Seeded tasks owned by alice.
ALICE_TASK_IDS = {"task-1", "task-2"}
BOB_TASK_IDS = {"task-3"}
