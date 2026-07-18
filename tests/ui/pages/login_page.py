"""Playwright page object for the login screen."""

from __future__ import annotations

from playwright.sync_api import Locator, Page, expect

from tests.helpers.config import BASE_URL


class LoginPage:
    def __init__(self, page: Page, base_url: str = BASE_URL) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def open(self) -> None:
        self.page.goto(f"{self.base_url}/login")
        expect(self.form).to_be_visible()

    @property
    def form(self) -> Locator:
        return self.page.get_by_test_id("login-form")

    @property
    def username_input(self) -> Locator:
        return self.page.get_by_test_id("username-input")

    @property
    def password_input(self) -> Locator:
        return self.page.get_by_test_id("password-input")

    @property
    def submit_button(self) -> Locator:
        return self.page.get_by_test_id("login-submit")

    @property
    def error_alert(self) -> Locator:
        return self.page.get_by_test_id("login-error")

    def login(self, username: str, password: str) -> None:
        self.username_input.fill(username)
        self.password_input.fill(password)
        self.submit_button.click()
