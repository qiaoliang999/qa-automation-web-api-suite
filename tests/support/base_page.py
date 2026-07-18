"""Page Object base class with shared navigation helpers."""

from __future__ import annotations

from playwright.sync_api import Page, expect

from tests.support.config import BASE_URL


class BasePage:
    path: str = "/"

    def __init__(self, page: Page, base_url: str = BASE_URL) -> None:
        self.page = page
        self.base_url = base_url.rstrip("/")

    def goto(self, path: str | None = None) -> None:
        target = path if path is not None else self.path
        self.page.goto(f"{self.base_url}{target}")

    def expect_url_contains(self, fragment: str) -> None:
        expect(self.page).to_have_url(lambda url: fragment in url)
