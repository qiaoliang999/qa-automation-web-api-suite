"""SQLite-backed store with seeded users/tasks and test reset support."""

from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime
from pathlib import Path
from threading import Lock

from app.auth import generate_token, hash_password, utc_now
from app.models import Task, User

# Default file DB for manual runs; tests override via TASKTRACK_DB.
_DEFAULT_DB = Path(__file__).resolve().parents[1] / "tasktrack.db"

# Cache seed hashes so reset() does not recompute pbkdf2 every test.
_SEED_PASSWORD_HASHES: dict[str, str] | None = None


def _seed_password_hashes() -> dict[str, str]:
    global _SEED_PASSWORD_HASHES
    if _SEED_PASSWORD_HASHES is None:
        _SEED_PASSWORD_HASHES = {
            "alice123": hash_password("alice123"),
            "bob1234": hash_password("bob1234"),
            "admin123": hash_password("admin123"),
        }
    return _SEED_PASSWORD_HASHES


def _db_path() -> str:
    return os.getenv("TASKTRACK_DB", str(_DEFAULT_DB))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class DataStore:
    """Process-local SQLite store. Call reset() between tests for isolation."""

    def __init__(self, path: str | None = None) -> None:
        self._lock = Lock()
        self.path = path or _db_path()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        if self._user_count() == 0:
            self.seed()

    def _init_schema(self) -> None:
        with self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user'
                );
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'todo',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    due_date TEXT,
                    owner_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (owner_id) REFERENCES users(id)
                );
                CREATE TABLE IF NOT EXISTS tokens (
                    token TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                );
                """
            )

    def _user_count(self) -> int:
        row = self._conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        return int(row["c"])

    def reconfigure(self, path: str) -> None:
        """Point the store at a new SQLite file (used by tests)."""
        with self._lock:
            self._conn.close()
            self.path = path
            self._conn = sqlite3.connect(self.path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
            self._seed_unlocked()

    def seed(self) -> None:
        """Load deterministic seed data used by the automated suite."""
        with self._lock:
            self._seed_unlocked()

    def _seed_unlocked(self) -> None:
        """Seed implementation; caller must hold self._lock."""
        hashes = _seed_password_hashes()
        with self._conn:
            self._conn.execute("DELETE FROM tokens")
            self._conn.execute("DELETE FROM tasks")
            self._conn.execute("DELETE FROM users")

            users = [
                User(
                    id="user-alice",
                    username="alice",
                    password_hash=hashes["alice123"],
                    display_name="Alice Anderson",
                    role="user",
                ),
                User(
                    id="user-bob",
                    username="bob",
                    password_hash=hashes["bob1234"],
                    display_name="Bob Baker",
                    role="user",
                ),
                User(
                    id="user-admin",
                    username="admin",
                    password_hash=hashes["admin123"],
                    display_name="Admin User",
                    role="admin",
                ),
            ]
            for user in users:
                self._insert_user(user)

            now = utc_now().isoformat()
            tasks = [
                Task(
                    id="task-1",
                    title="Write test plan",
                    description="Outline smoke and regression coverage for TaskTrack.",
                    status="todo",
                    priority="high",
                    due_date=date(2026, 8, 1),
                    owner_id="user-alice",
                ),
                Task(
                    id="task-2",
                    title="Review API contract",
                    description="Validate request/response schemas for tasks endpoints.",
                    status="in_progress",
                    priority="medium",
                    due_date=None,
                    owner_id="user-alice",
                ),
                Task(
                    id="task-3",
                    title="Prepare demo data",
                    description="Seed accounts and sample tasks for QA runs.",
                    status="done",
                    priority="low",
                    due_date=date(2026, 7, 1),
                    owner_id="user-bob",
                ),
                Task(
                    id="task-4",
                    title="Audit access control",
                    description="Review admin vs user list visibility.",
                    status="todo",
                    priority="high",
                    due_date=date(2026, 9, 15),
                    owner_id="user-admin",
                ),
            ]
            for task in tasks:
                self._conn.execute(
                    """
                    INSERT INTO tasks
                    (id, title, description, status, priority, due_date,
                     owner_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.title,
                        task.description,
                        task.status,
                        task.priority,
                        task.due_date.isoformat() if task.due_date else None,
                        task.owner_id,
                        now,
                        now,
                    ),
                )

    def reset(self) -> None:
        self.seed()

    def _insert_user(self, user: User) -> None:
        self._conn.execute(
            """
            INSERT INTO users (id, username, password_hash, display_name, role)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user.id, user.username, user.password_hash, user.display_name, user.role),
        )

    def _row_to_user(self, row: sqlite3.Row) -> User:
        return User(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            display_name=row["display_name"],
            role=row["role"],
        )

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        return Task(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            priority=row["priority"],
            due_date=_parse_date(row["due_date"]),
            owner_id=row["owner_id"],
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def find_user_by_username(self, username: str) -> User | None:
        row = self._conn.execute(
            "SELECT * FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def find_user_by_id(self, user_id: str) -> User | None:
        row = self._conn.execute(
            "SELECT * FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        return self._row_to_user(row) if row else None

    def create_user(self, user: User) -> User:
        with self._lock:
            with self._conn:
                self._insert_user(user)
        return user

    def create_token(self, user_id: str) -> str:
        token = generate_token()
        with self._lock:
            with self._conn:
                self._conn.execute(
                    "INSERT INTO tokens (token, user_id) VALUES (?, ?)",
                    (token, user_id),
                )
        return token

    def user_for_token(self, token: str) -> User | None:
        row = self._conn.execute(
            "SELECT user_id FROM tokens WHERE token = ?",
            (token,),
        ).fetchone()
        if not row:
            return None
        return self.find_user_by_id(row["user_id"])

    def revoke_token(self, token: str) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute("DELETE FROM tokens WHERE token = ?", (token,))

    def get_task(self, task_id: str) -> Task | None:
        row = self._conn.execute(
            "SELECT * FROM tasks WHERE id = ?",
            (task_id,),
        ).fetchone()
        return self._row_to_task(row) if row else None

    def create_task(self, task: Task) -> Task:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    INSERT INTO tasks
                    (id, title, description, status, priority, due_date,
                     owner_id, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task.id,
                        task.title,
                        task.description,
                        task.status,
                        task.priority,
                        task.due_date.isoformat() if task.due_date else None,
                        task.owner_id,
                        task.created_at.isoformat(),
                        task.updated_at.isoformat(),
                    ),
                )
        return task

    def save_task(self, task: Task) -> Task:
        with self._lock:
            with self._conn:
                self._conn.execute(
                    """
                    UPDATE tasks
                    SET title = ?, description = ?, status = ?, priority = ?,
                        due_date = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (
                        task.title,
                        task.description,
                        task.status,
                        task.priority,
                        task.due_date.isoformat() if task.due_date else None,
                        task.updated_at.isoformat(),
                        task.id,
                    ),
                )
        return task

    def delete_task(self, task_id: str) -> None:
        with self._lock:
            with self._conn:
                self._conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))

    def list_tasks(
        self,
        *,
        owner_id: str | None = None,
        status: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Task], int]:
        clauses: list[str] = []
        params: list[object] = []
        if owner_id is not None:
            clauses.append("owner_id = ?")
            params.append(owner_id)
        if status is not None:
            clauses.append("status = ?")
            params.append(status)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        total_row = self._conn.execute(
            f"SELECT COUNT(*) AS c FROM tasks {where}",
            params,
        ).fetchone()
        total = int(total_row["c"])

        offset = max(page - 1, 0) * page_size
        rows = self._conn.execute(
            f"""
            SELECT * FROM tasks {where}
            ORDER BY created_at ASC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
        return [self._row_to_task(row) for row in rows], total


db = DataStore()
