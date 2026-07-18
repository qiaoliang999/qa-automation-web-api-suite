"""In-memory data store with seeded users and tasks for deterministic tests."""

from __future__ import annotations

from copy import deepcopy
from threading import Lock

from app.models import Task, User, utc_now


class DataStore:
    """Simple process-local store. Reset between tests via reset()."""

    def __init__(self) -> None:
        self._lock = Lock()
        self.users: dict[str, User] = {}
        self.tasks: dict[str, Task] = {}
        self.tokens: dict[str, str] = {}  # token -> user_id
        self.seed()

    def seed(self) -> None:
        """Load predictable seed data used by automated tests."""
        alice = User(
            id="user-alice",
            username="alice",
            password="alice123",
            display_name="Alice Anderson",
        )
        bob = User(
            id="user-bob",
            username="bob",
            password="bob1234",
            display_name="Bob Baker",
        )
        self.users = {alice.id: alice, bob.id: bob}
        self.tasks = {
            "task-1": Task(
                id="task-1",
                title="Write test plan",
                description="Outline smoke and regression coverage for TaskTrack.",
                status="todo",
                owner_id=alice.id,
            ),
            "task-2": Task(
                id="task-2",
                title="Review API contract",
                description="Validate request/response schemas for tasks endpoints.",
                status="in_progress",
                owner_id=alice.id,
            ),
            "task-3": Task(
                id="task-3",
                title="Prepare demo data",
                description="Seed accounts and sample tasks for QA runs.",
                status="done",
                owner_id=bob.id,
            ),
        }
        self.tokens = {}

    def reset(self) -> None:
        with self._lock:
            self.seed()

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "users": deepcopy(self.users),
                "tasks": deepcopy(self.tasks),
                "tokens": deepcopy(self.tokens),
            }

    def find_user_by_username(self, username: str) -> User | None:
        for user in self.users.values():
            if user.username == username:
                return user
        return None

    def create_token(self, user_id: str) -> str:
        token = f"tok-{user_id}-{utc_now().timestamp()}"
        self.tokens[token] = user_id
        return token

    def user_for_token(self, token: str) -> User | None:
        user_id = self.tokens.get(token)
        if not user_id:
            return None
        return self.users.get(user_id)

    def revoke_token(self, token: str) -> None:
        self.tokens.pop(token, None)


db = DataStore()
