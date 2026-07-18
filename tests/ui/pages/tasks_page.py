"""Playwright page object for the tasks dashboard."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.helpers.config import BASE_URL


class TasksPage:
    def __init__(self, page: Page, base_url: str = BASE_URL) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self) -> None:
        self.page.goto(f"{self.base_url}/tasks")

    @property
    def heading(self) -> Locator:
        return self.page.get_by_test_id("tasks-heading")

    @property
    def greeting(self) -> Locator:
        return self.page.get_by_test_id("user-greeting")

    @property
    def logout_button(self) -> Locator:
        return self.page.get_by_test_id("logout-button")

    @property
    def create_form(self) -> Locator:
        return self.page.get_by_test_id("create-task-form")

    @property
    def title_input(self) -> Locator:
        return self.page.get_by_test_id("task-title-input")

    @property
    def description_input(self) -> Locator:
        return self.page.get_by_test_id("task-description-input")

    @property
    def status_select(self) -> Locator:
        return self.page.get_by_test_id("task-status-select")

    @property
    def create_submit(self) -> Locator:
        return self.page.get_by_test_id("create-task-submit")

    @property
    def form_error(self) -> Locator:
        return self.page.get_by_test_id("form-error")

    @property
    def form_success(self) -> Locator:
        return self.page.get_by_test_id("form-success")

    @property
    def task_list(self) -> Locator:
        return self.page.get_by_test_id("task-list")

    @property
    def task_items(self) -> Locator:
        return self.page.get_by_test_id("task-item")

    @property
    def task_count(self) -> Locator:
        return self.page.get_by_test_id("task-count")

    def expect_loaded(self) -> None:
        expect(self.heading).to_be_visible()
        expect(self.create_form).to_be_visible()

    def create_task(
        self,
        title: str,
        description: str = "",
        status: str = "todo",
    ) -> None:
        self.title_input.fill(title)
        self.description_input.fill(description)
        self.status_select.select_option(status)
        self.create_submit.click()

    def task_by_title(self, title: str) -> Locator:
        return self.task_items.filter(has_text=title).first

    def delete_task(self, title: str) -> None:
        item = self.task_by_title(title)
        item.get_by_test_id("delete-task-button").click()

    def update_status(self, title: str, status: str) -> None:
        item = self.task_by_title(title)
        item.get_by_test_id("status-change-select").select_option(status)
        item.get_by_test_id("status-change-submit").click()
