"""Pytest fixtures: server lifecycle, API clients, Playwright browser."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest
from playwright.sync_api import Page, sync_playwright

from tests.helpers.api_client import ApiClient
from tests.helpers.config import BASE_URL

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = ROOT / "artifacts" / "screenshots"


def _wait_for_server(url: str, timeout: float = 30.0) -> None:
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            response = httpx.get(f"{url}/health", timeout=1.0)
            if response.status_code == 200:
                return
        except Exception as exc:  # noqa: BLE001 - connection retry loop
            last_error = exc
        time.sleep(0.25)
    raise RuntimeError(f"Server at {url} did not become ready: {last_error}")


@pytest.fixture(scope="session")
def base_url() -> str:
    return BASE_URL


@pytest.fixture(scope="session")
def app_server(base_url: str):
    """Start TaskTrack once per test session and tear it down afterward."""
    # If something is already serving /health, reuse it (useful for local debug).
    try:
        response = httpx.get(f"{base_url}/health", timeout=1.0)
        if response.status_code == 200:
            yield base_url
            return
    except Exception:
        pass

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


@pytest.fixture
def api_client(app_server: str) -> ApiClient:
    """Authenticated API client with a clean data store for each test."""
    client = ApiClient(base_url=app_server)
    reset = client.reset_data()
    assert reset.status_code == 200, reset.text
    yield client
    client.close()


@pytest.fixture
def alice_client(api_client: ApiClient) -> ApiClient:
    response = api_client.login_as("alice")
    assert response.status_code == 200, response.text
    return api_client


@pytest.fixture(scope="session")
def browser_context_args():
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture(scope="session")
def playwright_instance():
    with sync_playwright() as playwright:
        yield playwright


@pytest.fixture(scope="session")
def browser(playwright_instance, browser_context_args):
    browser = playwright_instance.chromium.launch(headless=True)
    yield browser
    browser.close()


@pytest.fixture
def context(browser, browser_context_args):
    context = browser.new_context(**browser_context_args)
    yield context
    context.close()


@pytest.fixture
def page(context, app_server: str, api_client: ApiClient) -> Page:
    """Fresh browser page with reset application data."""
    # api_client fixture already resets data; depend on it for isolation.
    _ = api_client
    page = context.new_page()
    page.set_default_timeout(10_000)
    yield page
    page.close()


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """Attach screenshot path on UI test failures."""
    outcome = yield
    report = outcome.get_result()
    if report.when != "call" or not report.failed:
        return
    page = item.funcargs.get("page")
    if page is None:
        return
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = item.nodeid.replace("/", "_").replace("::", "_").replace("\\", "_")
    screenshot_path = ARTIFACTS_DIR / f"{safe_name}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        report.sections.append(("screenshot", str(screenshot_path)))
    except Exception as exc:  # noqa: BLE001
        report.sections.append(("screenshot_error", str(exc)))
