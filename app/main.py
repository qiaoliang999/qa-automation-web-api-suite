"""TaskTrack — task manager used as the system under test."""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.auth import hash_password, utc_now, verify_password
from app.database import db
from app.models import (
    LoginRequest,
    Task,
    TaskCreate,
    TaskListResponse,
    TaskResponse,
    TaskUpdate,
    TokenResponse,
    User,
    UserCreate,
    UserResponse,
)

APP_DIR = Path(__file__).resolve().parent


def current_app_env() -> str:
    return os.getenv("APP_ENV", "development").lower()


templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

app = FastAPI(
    title="TaskTrack",
    description=(
        "Task manager (roles, priority, due dates, pagination) used as the "
        "system under test for a QA automation portfolio suite."
    ),
    version="2.0.0",
)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

security = HTTPBearer(auto_error=False)
COOKIE_NAME = "tasktrack_token"
VALID_STATUSES = {"todo", "in_progress", "done"}
VALID_PRIORITIES = {"low", "medium", "high"}


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> User:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user = db.user_for_token(credentials.credentials)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


def task_to_response(task: Task) -> TaskResponse:
    return TaskResponse.model_validate(task.model_dump())


def _user_from_request(request: Request) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return db.user_for_token(token)


def _can_access_task(user: User, task: Task) -> bool:
    return user.role == "admin" or task.owner_id == user.id


# ---------------------------------------------------------------------------
# Health / test helpers
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "tasktrack",
        "version": "2.0.0",
        "env": current_app_env(),
    }


@app.post("/api/test/reset", include_in_schema=False)
def reset_data() -> dict:
    """Reset seeded data. Available only when APP_ENV=test."""
    if current_app_env() != "test":
        raise HTTPException(status_code=404, detail="Not found")
    db.reset()
    return {"status": "reset", "env": "test"}


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------


@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate) -> TokenResponse:
    if db.find_user_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    if not payload.username or not payload.display_name:
        raise HTTPException(status_code=422, detail="Username and display name are required")
    user = User(
        username=payload.username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name,
        role="user",
    )
    db.create_user(user)
    token = db.create_token(user.id)
    return TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = db.find_user_by_username(payload.username)
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = db.create_token(user.id)
    return TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
        role=user.role,
    )


@app.get("/api/auth/me", response_model=UserResponse)
def me(current_user: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        display_name=current_user.display_name,
        role=current_user.role,
    )


# ---------------------------------------------------------------------------
# Tasks API
# ---------------------------------------------------------------------------


@app.get("/api/tasks", response_model=TaskListResponse)
def list_tasks(
    current_user: User = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: str | None = Query(None, alias="status"),
) -> TaskListResponse:
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(status_code=422, detail="Invalid status filter")

    owner_id = None if current_user.role == "admin" else current_user.id
    items, total = db.list_tasks(
        owner_id=owner_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return TaskListResponse(
        items=[task_to_response(t) for t in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    if not payload.title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    task = Task(
        title=payload.title,
        description=payload.description or "",
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        owner_id=current_user.id,
    )
    db.create_task(task)
    return task_to_response(task)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if not _can_access_task(current_user, task):
        raise HTTPException(status_code=403, detail="Forbidden")
    return task_to_response(task)


@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    # Only the owner may mutate; admin may read all but not hijack ownership edits.
    if task.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    if task.owner_id != current_user.id and current_user.role == "admin":
        # Admin may update any task (ops use case).
        pass

    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        title = data["title"] or ""
        if not title:
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        task.title = title
    if "description" in data and data["description"] is not None:
        task.description = data["description"]
    if "status" in data and data["status"] is not None:
        task.status = data["status"]
    if "priority" in data and data["priority"] is not None:
        task.priority = data["priority"]
    if "due_date" in data:
        task.due_date = data["due_date"]
    task.updated_at = utc_now()
    db.save_task(task)
    return task_to_response(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    task = db.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Forbidden")
    db.delete_task(task_id)


# ---------------------------------------------------------------------------
# HTML UI
# ---------------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    user = _user_from_request(request)
    if user:
        return RedirectResponse(url="/tasks", status_code=302)
    return RedirectResponse(url="/login", status_code=302)


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    user = _user_from_request(request)
    if user:
        return RedirectResponse(url="/tasks", status_code=302)
    return templates.TemplateResponse(request, "login.html", {"error": None, "user": None})


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.find_user_by_username(username)
    if user is None or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password", "user": None},
            status_code=401,
        )
    token = db.create_token(user.id)
    response = RedirectResponse(url="/tasks", status_code=302)
    response.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax")
    return response


@app.post("/logout")
def logout(request: Request):
    token = request.cookies.get(COOKIE_NAME)
    if token:
        db.revoke_token(token)
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


def _tasks_for_ui(user: User) -> list[Task]:
    owner_id = None if user.role == "admin" else user.id
    tasks, _ = db.list_tasks(owner_id=owner_id, page=1, page_size=100)
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return tasks


@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "user": user,
            "tasks": _tasks_for_ui(user),
            "error": None,
            "success": None,
        },
    )


@app.post("/tasks", response_class=HTMLResponse)
def create_task_ui(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status_value: str = Form("todo"),
    priority_value: str = Form("medium"),
    due_date: str = Form(""),
):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    title = title.strip()
    description = description.strip()
    due = due_date.strip() or None
    error = None
    success = None

    if not title:
        error = "Title is required"
    elif len(title) > 120:
        error = "Title must be 120 characters or fewer"
    elif status_value not in VALID_STATUSES:
        error = "Invalid status"
    elif priority_value not in VALID_PRIORITIES:
        error = "Invalid priority"
    else:
        parsed_due = None
        if due:
            try:
                from datetime import date as date_cls

                parsed_due = date_cls.fromisoformat(due)
            except ValueError:
                error = "Invalid due date"
        if error is None:
            task = Task(
                title=title,
                description=description,
                status=status_value,  # type: ignore[arg-type]
                priority=priority_value,  # type: ignore[arg-type]
                due_date=parsed_due,
                owner_id=user.id,
            )
            db.create_task(task)
            success = f"Task '{task.title}' created"

    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "user": user,
            "tasks": _tasks_for_ui(user),
            "error": error,
            "success": success,
        },
        status_code=400 if error else 200,
    )


@app.post("/tasks/{task_id}/status", response_class=HTMLResponse)
def update_status_ui(request: Request, task_id: str, status_value: str = Form(...)):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    error = None
    success = None
    task = db.get_task(task_id)
    if task is None or not _can_access_task(user, task):
        error = "Task not found"
    elif task.owner_id != user.id and user.role != "admin":
        error = "Task not found"
    elif status_value not in VALID_STATUSES:
        error = "Invalid status"
    else:
        # Owner or admin may update status.
        if task.owner_id != user.id and user.role != "admin":
            error = "Task not found"
        else:
            task.status = status_value  # type: ignore[assignment]
            task.updated_at = utc_now()
            db.save_task(task)
            success = f"Updated status of '{task.title}' to {status_value}"

    return templates.TemplateResponse(
        request,
        "tasks.html",
        {
            "user": user,
            "tasks": _tasks_for_ui(user),
            "error": error,
            "success": success,
        },
        status_code=400 if error else 200,
    )


@app.post("/tasks/{task_id}/delete")
def delete_task_ui(request: Request, task_id: str):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    task = db.get_task(task_id)
    if task and (task.owner_id == user.id or user.role == "admin"):
        db.delete_task(task_id)
    return RedirectResponse(url="/tasks", status_code=302)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
