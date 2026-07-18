"""TaskTrack — a small task manager used as the system under test."""

from __future__ import annotations

from pathlib import Path

from fastapi import Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import db
from app.models import (
    Task,
    TaskCreate,
    TaskResponse,
    TaskUpdate,
    TokenResponse,
    User,
    UserCreate,
    LoginRequest,
    utc_now,
)

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(APP_DIR / "templates"))

app = FastAPI(
    title="TaskTrack",
    description="Demo task manager used as the system under test for a QA automation portfolio.",
    version="1.0.0",
)
app.mount("/static", StaticFiles(directory=str(APP_DIR / "static")), name="static")

security = HTTPBearer(auto_error=False)


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


# ---------------------------------------------------------------------------
# Health / admin helpers (used by tests to reset state)
# ---------------------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "tasktrack"}


@app.post("/api/test/reset", include_in_schema=False)
def reset_data() -> dict:
    """Reset seeded data. Intended for test isolation only."""
    db.reset()
    return {"status": "reset"}


# ---------------------------------------------------------------------------
# Auth API
# ---------------------------------------------------------------------------


@app.post("/api/auth/register", response_model=TokenResponse, status_code=201)
def register(payload: UserCreate) -> TokenResponse:
    if db.find_user_by_username(payload.username):
        raise HTTPException(status_code=409, detail="Username already exists")
    user = User(
        username=payload.username,
        password=payload.password,
        display_name=payload.display_name,
    )
    db.users[user.id] = user
    token = db.create_token(user.id)
    return TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
    )


@app.post("/api/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest) -> TokenResponse:
    user = db.find_user_by_username(payload.username)
    if user is None or user.password != payload.password:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = db.create_token(user.id)
    return TokenResponse(
        access_token=token,
        username=user.username,
        display_name=user.display_name,
    )


@app.get("/api/auth/me")
def me(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "id": current_user.id,
        "username": current_user.username,
        "display_name": current_user.display_name,
    }


# ---------------------------------------------------------------------------
# Tasks API
# ---------------------------------------------------------------------------


@app.get("/api/tasks", response_model=list[TaskResponse])
def list_tasks(current_user: User = Depends(get_current_user)) -> list[TaskResponse]:
    owned = [t for t in db.tasks.values() if t.owner_id == current_user.id]
    owned.sort(key=lambda t: t.created_at)
    return [task_to_response(t) for t in owned]


@app.post("/api/tasks", response_model=TaskResponse, status_code=201)
def create_task(
    payload: TaskCreate,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Title cannot be empty")
    task = Task(
        title=title,
        description=payload.description.strip(),
        status=payload.status,
        owner_id=current_user.id,
    )
    db.tasks[task.id] = task
    return task_to_response(task)


@app.get("/api/tasks/{task_id}", response_model=TaskResponse)
def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return task_to_response(task)


@app.put("/api/tasks/{task_id}", response_model=TaskResponse)
def update_task(
    task_id: str,
    payload: TaskUpdate,
    current_user: User = Depends(get_current_user),
) -> TaskResponse:
    task = db.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")

    data = payload.model_dump(exclude_unset=True)
    if "title" in data:
        title = (data["title"] or "").strip()
        if not title:
            raise HTTPException(status_code=422, detail="Title cannot be empty")
        task.title = title
    if "description" in data and data["description"] is not None:
        task.description = data["description"].strip()
    if "status" in data and data["status"] is not None:
        task.status = data["status"]
    task.updated_at = utc_now()
    db.tasks[task.id] = task
    return task_to_response(task)


@app.delete("/api/tasks/{task_id}", status_code=204)
def delete_task(
    task_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    task = db.tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    del db.tasks[task_id]


# ---------------------------------------------------------------------------
# HTML UI (cookie-token based for simple browser flows)
# ---------------------------------------------------------------------------

COOKIE_NAME = "tasktrack_token"


def _user_from_request(request: Request) -> User | None:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    return db.user_for_token(token)


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
    return templates.TemplateResponse(
        request,
        "login.html",
        {"error": None},
    )


@app.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    user = db.find_user_by_username(username)
    if user is None or user.password != password:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"error": "Invalid username or password"},
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


@app.get("/tasks", response_class=HTMLResponse)
def tasks_page(request: Request):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    tasks = [t for t in db.tasks.values() if t.owner_id == user.id]
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"user": user, "tasks": tasks, "error": None, "success": None},
    )


@app.post("/tasks", response_class=HTMLResponse)
def create_task_ui(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    status_value: str = Form("todo"),
):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    title = title.strip()
    error = None
    success = None
    if not title:
        error = "Title is required"
    elif status_value not in {"todo", "in_progress", "done"}:
        error = "Invalid status"
    else:
        task = Task(
            title=title,
            description=description.strip(),
            status=status_value,  # type: ignore[arg-type]
            owner_id=user.id,
        )
        db.tasks[task.id] = task
        success = f"Task '{task.title}' created"

    tasks = [t for t in db.tasks.values() if t.owner_id == user.id]
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    status_code = 400 if error else 200
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"user": user, "tasks": tasks, "error": error, "success": success},
        status_code=status_code,
    )


@app.post("/tasks/{task_id}/status", response_class=HTMLResponse)
def update_status_ui(request: Request, task_id: str, status_value: str = Form(...)):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)

    error = None
    success = None
    task = db.tasks.get(task_id)
    if task is None or task.owner_id != user.id:
        error = "Task not found"
    elif status_value not in {"todo", "in_progress", "done"}:
        error = "Invalid status"
    else:
        task.status = status_value  # type: ignore[assignment]
        task.updated_at = utc_now()
        db.tasks[task.id] = task
        success = f"Updated status of '{task.title}' to {status_value}"

    tasks = [t for t in db.tasks.values() if t.owner_id == user.id]
    tasks.sort(key=lambda t: t.created_at, reverse=True)
    return templates.TemplateResponse(
        request,
        "tasks.html",
        {"user": user, "tasks": tasks, "error": error, "success": success},
        status_code=400 if error else 200,
    )


@app.post("/tasks/{task_id}/delete")
def delete_task_ui(request: Request, task_id: str):
    user = _user_from_request(request)
    if user is None:
        return RedirectResponse(url="/login", status_code=302)
    task = db.tasks.get(task_id)
    if task and task.owner_id == user.id:
        del db.tasks[task_id]
    return RedirectResponse(url="/tasks", status_code=302)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
