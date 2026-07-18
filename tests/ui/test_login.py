"""UI tests for authentication flows."""

from __future__ import annotations

import re

import pytest
from playwright.sync_api import Page, expect

from tests.support.config import USERS
from tests.ui.pages.login_page import LoginPage
from tests.ui.pages.tasks_page import TasksPage


@pytest.mark.ui
@pytest.mark.smoke
def test_login_success(page: Page):
    login = LoginPage(page)
    login.open()
    user = USERS["alice"]
    login.login(user["username"], user["password"])

    tasks = TasksPage(page)
    tasks.expect_loaded()
    expect(tasks.greeting).to_contain_text(user["display_name"])
    expect(page).to_have_url(re.compile(r".*/tasks/?$"))


@pytest.mark.ui
def test_login_failure_shows_error(page: Page):
    login = LoginPage(page)
    login.open()
    login.login("alice", "not-the-password")

    expect(login.error_alert).to_be_visible()
    expect(login.error_alert).to_have_text("Invalid username or password")
    expect(page).to_have_url(re.compile(r".*/login"))


@pytest.mark.ui
def test_logout_returns_to_login(authenticated_page: Page):
    tasks = TasksPage(authenticated_page)
    tasks.open()
    tasks.expect_loaded()
    tasks.logout_button.click()

    login_after = LoginPage(authenticated_page)
    expect(login_after.form).to_be_visible()
    expect(authenticated_page).to_have_url(re.compile(r".*/login"))


@pytest.mark.ui
def test_tasks_page_requires_login(page: Page, base_url: str):
    page.goto(f"{base_url}/tasks")
    expect(page).to_have_url(re.compile(r".*/login"))
    login = LoginPage(page)
    expect(login.form).to_be_visible()


@pytest.mark.ui
def test_admin_login_shows_role(page: Page):
    login = LoginPage(page)
    login.open()
    admin = USERS["admin"]
    login.login(admin["username"], admin["password"])
    tasks = TasksPage(page)
    tasks.expect_loaded()
    expect(tasks.greeting).to_contain_text(admin["display_name"])
    expect(page.get_by_test_id("user-role")).to_have_text("admin")
    expect(page.get_by_test_id("tasks-heading")).to_have_text("All Tasks")
