"""UI tests for the core task workflow."""

from __future__ import annotations

import pytest
from playwright.sync_api import Page, expect

from tests.helpers.config import USERS
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.tasks_page import TasksPage


def _login_as_alice(page: Page) -> TasksPage:
    login = LoginPage(page)
    login.open()
    user = USERS["alice"]
    login.login(user["username"], user["password"])
    tasks = TasksPage(page)
    tasks.expect_loaded()
    return tasks


@pytest.mark.ui
@pytest.mark.smoke
def test_create_task_happy_path(page: Page):
    tasks = _login_as_alice(page)
    initial_count = int(tasks.task_count.inner_text())

    tasks.create_task(
        title="Review CI pipeline",
        description="Ensure green build before merge",
        status="in_progress",
    )

    expect(tasks.form_success).to_be_visible()
    expect(tasks.form_success).to_contain_text("Review CI pipeline")
    expect(tasks.task_by_title("Review CI pipeline")).to_be_visible()
    expect(tasks.task_count).to_have_text(str(initial_count + 1))

    item = tasks.task_by_title("Review CI pipeline")
    expect(item.get_by_test_id("task-status")).to_have_text("in_progress")
    expect(item.get_by_test_id("task-description")).to_have_text(
        "Ensure green build before merge"
    )


@pytest.mark.ui
def test_create_task_empty_title_negative(page: Page):
    tasks = _login_as_alice(page)
    tasks.create_task(title="   ", description="should fail")

    expect(tasks.form_error).to_be_visible()
    expect(tasks.form_error).to_have_text("Title is required")


@pytest.mark.ui
def test_update_task_status(page: Page):
    tasks = _login_as_alice(page)
    # Seeded task for alice
    item = tasks.task_by_title("Write test plan")
    expect(item).to_be_visible()

    tasks.update_status("Write test plan", "done")
    expect(tasks.form_success).to_contain_text("Write test plan")
    expect(
        tasks.task_by_title("Write test plan").get_by_test_id("task-status")
    ).to_have_text("done")


@pytest.mark.ui
def test_delete_task(page: Page):
    tasks = _login_as_alice(page)
    tasks.create_task(title="Disposable UI task", description="remove me")
    expect(tasks.task_by_title("Disposable UI task")).to_be_visible()

    tasks.delete_task("Disposable UI task")
    expect(tasks.task_by_title("Disposable UI task")).to_have_count(0)


@pytest.mark.ui
def test_seeded_tasks_visible_after_login(page: Page):
    tasks = _login_as_alice(page)
    expect(tasks.task_by_title("Write test plan")).to_be_visible()
    expect(tasks.task_by_title("Review API contract")).to_be_visible()
    # Bob's task must not appear for alice
    expect(page.get_by_text("Prepare demo data")).to_have_count(0)
