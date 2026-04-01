from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import Browser, Page, Playwright


@contextmanager
def launched_chromium(
    playwright: Playwright,
    *,
    headless: bool = True,
) -> Iterator[Browser]:
    browser = playwright.chromium.launch(headless=headless)
    try:
        yield browser
    finally:
        browser.close()


def wait_for_page_ready(
    page: Page,
    ready_selector: str,
    *,
    timeout_ms: int = 5000,
    settle_ms: int = 1200,
) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(settle_ms)
    try:
        page.locator(ready_selector).first.wait_for(timeout=timeout_ms)
    except Exception:
        pass


def click_if_visible(
    page: Page,
    selector: str,
    *,
    timeout_ms: int = 2000,
    settle_ms: int = 500,
) -> bool:
    try:
        element = page.locator(selector).first
        if element.count() == 0 or not element.is_visible():
            return False

        element.click(timeout=timeout_ms)
        page.wait_for_timeout(settle_ms)
        return True
    except Exception:
        return False
