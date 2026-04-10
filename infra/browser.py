from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Sequence

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
    """Wait for DOM content, pause briefly, then wait for `ready_selector`.

    Args:
        page: Playwright page to wait on.
        ready_selector: Selector that marks the page as ready for interaction.
        timeout_ms: Maximum time to wait for `ready_selector`.
        settle_ms: Extra delay after DOM load to let UI updates settle.
    """
    prepare_page(
        page,
        wait_for=[ready_selector],
        wait_timeout_ms=timeout_ms,
        wait_settle_ms=settle_ms,
    )


def open_page(
    page: Page,
    url: str,
    *,
    wait_until: str = "domcontentloaded",
    timeout_ms: int = 30000,
) -> None:
    """Open `url` with the default page-load settings used by this project.

    Args:
        page: Playwright page to navigate.
        url: Absolute or relative URL to open.
        wait_until: Playwright load state to wait for.
        timeout_ms: Maximum time allowed for the navigation.
    """
    page.goto(url, wait_until=wait_until, timeout=timeout_ms)


def open_and_prepare_page(
    page: Page,
    url: str,
    *,
    wait_for: Sequence[str] = (),
    click_if_visible_selectors: Sequence[str] = (),
    open_wait_until: str = "domcontentloaded",
    open_timeout_ms: int = 30000,
    wait_timeout_ms: int = 5000,
    wait_settle_ms: int = 1200,
    click_timeout_ms: int = 2000,
    click_settle_ms: int = 500,
) -> list[str]:
    """Open `url`, then wait and optionally click selectors on the loaded page.

    Args:
        page: Playwright page to navigate and prepare.
        url: Absolute or relative URL to open.
        wait_for: Selectors that should be waited for before interaction.
        click_if_visible_selectors: Selectors to click when visible.
        open_wait_until: Playwright load state to wait for during navigation.
        open_timeout_ms: Maximum time allowed for the navigation.
        wait_timeout_ms: Maximum time to wait for each selector in `wait_for`.
        wait_settle_ms: Extra delay after DOM load to let UI updates settle.
        click_timeout_ms: Maximum time allowed for each click action.
        click_settle_ms: Extra delay after each click to let UI updates settle.
    """
    open_page(
        page,
        url,
        wait_until=open_wait_until,
        timeout_ms=open_timeout_ms,
    )
    return prepare_page(
        page,
        wait_for=wait_for,
        click_if_visible_selectors=click_if_visible_selectors,
        wait_timeout_ms=wait_timeout_ms,
        wait_settle_ms=wait_settle_ms,
        click_timeout_ms=click_timeout_ms,
        click_settle_ms=click_settle_ms,
    )


def capture_page_html(page: Page) -> str | None:
    """Return the current page HTML, or `None` when Playwright cannot provide it."""
    try:
        return page.content()
    except Exception:
        return None


def capture_page_title(page: Page) -> str | None:
    """Return the current page title, or `None` when Playwright cannot provide it."""
    try:
        title = page.title().strip()
        return title or None
    except Exception:
        return None


def click_if_visible(
    page: Page,
    selector: str,
    *,
    timeout_ms: int = 2000,
    settle_ms: int = 500,
) -> bool:
    """Click `selector` when it exists and is visible.

    Args:
        page: Playwright page to inspect.
        selector: Selector for the element to click.
        timeout_ms: Maximum time allowed for the click action.
        settle_ms: Extra delay after clicking to let UI updates settle.
    """
    try:
        element = page.locator(selector).first
        if element.count() == 0 or not element.is_visible():
            return False

        element.click(timeout=timeout_ms)
        page.wait_for_timeout(settle_ms)
        return True
    except Exception:
        return False


def prepare_page(
    page: Page,
    *,
    wait_for: Sequence[str] = (),
    click_if_visible_selectors: Sequence[str] = (),
    wait_timeout_ms: int = 5000,
    wait_settle_ms: int = 1200,
    click_timeout_ms: int = 2000,
    click_settle_ms: int = 500,
) -> list[str]:
    """Wait for a page to settle, then wait and optionally click selectors.

    Args:
        page: Playwright page to prepare.
        wait_for: Selectors that should be waited for before interaction.
        click_if_visible_selectors: Selectors to click when visible.
        wait_timeout_ms: Maximum time to wait for each selector in `wait_for`.
        wait_settle_ms: Extra delay after DOM load to let UI updates settle.
        click_timeout_ms: Maximum time allowed for each click action.
        click_settle_ms: Extra delay after each click to let UI updates settle.
    """
    clicked_selectors: list[str] = []

    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(wait_settle_ms)

    for selector in wait_for:
        try:
            page.locator(selector).first.wait_for(timeout=wait_timeout_ms)
        except Exception:
            pass

    for selector in click_if_visible_selectors:
        if click_if_visible(
            page,
            selector,
            timeout_ms=click_timeout_ms,
            settle_ms=click_settle_ms,
        ):
            clicked_selectors.append(selector)

    return clicked_selectors
