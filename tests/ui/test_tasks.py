"""UI tests for the core task workflow (API-seeded auth where possible)."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.support.api_client import ApiClient
from tests.ui.pages.tasks_page import TasksPage


@pytest.mark.ui
@pytest.mark.smoke
def test_create_task_happy_path(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    initial_count = int(tasks.task_count.inner_text())

    tasks.create_task(
        title="Review CI pipeline",
        description="Ensure green build before merge",
        status="in_progress",
        priority="high",
        due_date="2026-12-15",
    )

    expect(tasks.form_success).to_be_visible()
    expect(tasks.form_success).to_contain_text("Review CI pipeline")
    expect(tasks.task_by_title("Review CI pipeline")).to_be_visible()
    expect(tasks.task_count).to_have_text(str(initial_count + 1))

    item = tasks.task_by_title("Review CI pipeline")
    expect(item.get_by_test_id("task-status")).to_have_text("in_progress")
    expect(item.get_by_test_id("task-priority")).to_have_text("high")
    expect(item.get_by_test_id("task-description")).to_have_text(
        "Ensure green build before merge"
    )


@pytest.mark.ui
def test_create_task_empty_title_negative(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    tasks.create_task(title="   ", description="should fail")

    expect(tasks.form_error).to_be_visible()
    expect(tasks.form_error).to_have_text("Title is required")


@pytest.mark.ui
def test_update_task_status(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    item = tasks.task_by_title("Write test plan")
    expect(item).to_be_visible()

    tasks.update_status("Write test plan", "done")
    expect(tasks.form_success).to_contain_text("Write test plan")
    expect(
        tasks.task_by_title("Write test plan").get_by_test_id("task-status")
    ).to_have_text("done")


@pytest.mark.ui
def test_delete_task(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    tasks.create_task(title="Disposable UI task", description="remove me")
    expect(tasks.task_by_title("Disposable UI task")).to_be_visible()

    tasks.delete_task("Disposable UI task")
    expect(tasks.task_by_title("Disposable UI task")).to_have_count(0)


@pytest.mark.ui
def test_seeded_tasks_visible_after_cookie_auth(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    expect(tasks.task_by_title("Write test plan")).to_be_visible()
    expect(tasks.task_by_title("Review API contract")).to_be_visible()
    # Bob's task must not appear for alice
    expect(authenticated_page.get_by_text("Prepare demo data")).to_have_count(0)


@pytest.mark.ui
def test_admin_sees_all_seeded_tasks(admin_page: Page):
    tasks = TasksPage(admin_page)
    tasks.open()
    tasks.expect_loaded()
    expect(tasks.task_by_title("Write test plan")).to_be_visible()
    expect(tasks.task_by_title("Prepare demo data")).to_be_visible()
    expect(tasks.task_by_title("Audit access control")).to_be_visible()
    expect(tasks.task_count).to_have_text("4")


@pytest.mark.ui
def test_api_seeded_task_appears_in_ui(authenticated_page: Page, live_api: ApiClient):
    """Hybrid: create via API, assert UI reflects it without form fill."""
    created = live_api.login_as("alice")
    assert created.status_code == 200
    create = live_api.create_task(
        title="API seeded for UI",
        description="visible without UI create",
        priority="low",
    )
    assert create.status_code == 201

    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    expect(tasks.task_by_title("API seeded for UI")).to_be_visible()
    expect(
        tasks.task_by_title("API seeded for UI").get_by_test_id("task-priority")
    ).to_have_text("low")
