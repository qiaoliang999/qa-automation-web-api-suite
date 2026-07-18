"""Pytest fixtures: in-process app for API, optional live server for UI."""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright

# Ensure APP_ENV=test before the application module is imported.
os.environ.setdefault("APP_ENV", "test")
# Keep pbkdf2 cheap in the suite while still exercising real hashing.
os.environ.setdefault("TASKTRACK_PBKDF2_ITERATIONS", "5000")

from app.database import db  # noqa: E402
from app.main import COOKIE_NAME, app  # noqa: E402
from tests.support.api_client import ApiClient  # noqa: E402
from tests.support.config import BASE_URL  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts" / "screenshots"
TRACES_DIR = ROOT / "artifacts" / "traces"


# ---------------------------------------------------------------------------
# In-process FastAPI app (API + contract tests)
# ---------------------------------------------------------------------------


@pytest.fixture()
def isolated_db(tmp_path: Path):
    """Point the shared store at a fresh SQLite file and reseed."""
    db_file = tmp_path / "test.db"
    db.reconfigure(str(db_file))
    yield db
    db.reset()


@pytest.fixture()
def api_client(isolated_db) -> ApiClient:
    """In-process FastAPI TestClient; clean seed data per test."""
    from fastapi.testclient import TestClient

    _ = isolated_db
    with TestClient(app) as test_client:
        client = ApiClient.from_test_client(test_client)
        yield client



@pytest.fixture()
def alice_client(api_client: ApiClient) -> ApiClient:
    return api_client.as_user("alice")


@pytest.fixture()
def bob_client(api_client: ApiClient) -> ApiClient:
    return api_client.as_user("bob")


@pytest.fixture()
def admin_client(api_client: ApiClient) -> ApiClient:
    return api_client.as_user("admin")


# ---------------------------------------------------------------------------
# Live server (UI tests only)
# ---------------------------------------------------------------------------


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{url}/health", timeout=1.0)
            if response.status_code == 200:
                return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Server at {url} did not become ready: {last_error}")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def app_server(base_url: str):
    """Start TaskTrack once per session for UI tests (APP_ENV=test)."""
    try:
        response = httpx.get(f"{base_url}/health", timeout=1.0)
        if response.status_code == 200:
            yield base_url
            return
    except Exception:
        pass

    db_file = tempfile.NamedTemporaryFile(prefix="tasktrack-ui-", suffix=".db", delete=False)
    db_path = db_file.name
    db_file.close()

    env = os.environ.copy()
    env["APP_ENV"] = "test"
    env["TASKTRACK_DB"] = db_path
    env["TASKTRACK_PBKDF2_ITERATIONS"] = os.getenv("TASKTRACK_PBKDF2_ITERATIONS", "5000")

    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--log-level",
            "warning",
        ],
        cwd=str(ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    try:
        _wait_for_server(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        try:
            Path(db_path).unlink(missing_ok=True)
        except OSError:
            pass


@pytest.fixture()
def live_api(app_server: str) -> ApiClient:
    """Network ApiClient against the live UI server; resets data per test."""
    client = ApiClient.from_base_url(app_server)
    reset = client.reset_data()
    assert reset.status_code == 200, reset.text
    yield client
    client.close()


# ---------------------------------------------------------------------------
# Playwright
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance) -> Browser:
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture()
def context(browser: Browser) -> BrowserContext:
    context = browser.new_context(
        viewport={"width": 1280, "height": 720},
        ignore_https_errors=True,
    )
    context.set_default_timeout(10_000)
    TRACES_DIR.mkdir(parents=True, exist_ok=True)
    context.tracing.start(screenshots=True, snapshots=True, sources=False)
    yield context
    context.close()


@pytest.fixture()
def page(context: BrowserContext, live_api: ApiClient) -> Page:
    """Fresh page with reset application data (via live_api)."""
    _ = live_api
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture()
def authenticated_page(context: BrowserContext, live_api: ApiClient, base_url: str) -> Page:
    """Browser page pre-authenticated as alice via API-issued session cookie."""
    login = live_api.login_as("alice")
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]

    context.add_cookies(
        [
            {
                "name": COOKIE_NAME,
                "value": token,
                "url": base_url,
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )
    page = context.new_page()
    yield page
    page.close()


@pytest.fixture()
def admin_page(context: BrowserContext, live_api: ApiClient, base_url: str) -> Page:
    """Browser page pre-authenticated as admin via cookie injection."""
    login = live_api.login_as("admin")
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    context.add_cookies(
        [
            {
                "name": COOKIE_NAME,
                "value": token,
                "url": base_url,
                "httpOnly": True,
                "sameSite": "Lax",
            }
        ]
    )
    page = context.new_page()
    yield page
    page.close()


# ---------------------------------------------------------------------------
# Failure evidence
# ---------------------------------------------------------------------------


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Screenshot + Playwright trace on UI failures."""
    outcome = yield
    report = outcome.get_result()
    setattr(item, f"rep_{report.when}", report)

    if report.when != "call":
        return

    context: BrowserContext | None = item.funcargs.get("context")
    page: Page | None = item.funcargs.get("page") or item.funcargs.get(
        "authenticated_page"
    ) or item.funcargs.get("admin_page")

    if not report.failed:
        if context is not None:
            try:
                context.tracing.stop()
            except Exception:
                pass
        return

    if page is not None:
        ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = (
            item.nodeid.replace("/", "_").replace("::", "_").replace("\\", "_").replace("[", "_").replace("]", "_")
        )
        screenshot_path = ARTIFACTS_DIR / f"{safe_name}.png"
        try:
            page.screenshot(path=str(screenshot_path), full_page=True)
            report.sections.append(("screenshot", str(screenshot_path)))
        except Exception as exc:  # noqa: BLE001
            report.sections.append(("screenshot_error", str(exc)))

    if context is not None:
        TRACES_DIR.mkdir(parents=True, exist_ok=True)
        safe_name = (
            item.nodeid.replace("/", "_").replace("::", "_").replace("\\", "_").replace("[", "_").replace("]", "_")
        )
        trace_path = TRACES_DIR / f"{safe_name}.zip"
        try:
            context.tracing.stop(path=str(trace_path))
            report.sections.append(("trace", str(trace_path)))
        except Exception as exc:  # noqa: BLE001
            report.sections.append(("trace_error", str(exc)))
