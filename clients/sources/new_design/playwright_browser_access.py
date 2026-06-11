from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from playwright.sync_api import BrowserContext, Error as PlaywrightError, Locator, Page

from clients.sources.new_design.browser_access import (
    BrowserAccess,
    BrowserAccessError,
    DOMElement,
    Selector,
    SelectorList,
)
from infra.browser import create_browser, open_and_prepare_page, open_page
from infra.logging import log


class PlaywrightDOMElement(DOMElement):
    """Playwright locator adapter for DOMElement reads.

    Keeps Playwright-specific locator operations inside the browser access
    realization while exposing only DOM text and attribute reads.
    """

    def __init__(self, locator: Locator) -> None:
        self._locator = locator

    def get_attribute(self, name: str) -> str | None:
        try:
            return self._locator.get_attribute(name)
        except PlaywrightError as exc:
            raise BrowserAccessError(
                f"Failed to read DOM element attribute: {name}"
            ) from exc

    def get_text(self, selector: str | None = None) -> str:
        try:
            if selector is None:
                return self._locator.inner_text()

            return self._locator.locator(selector).inner_text()
        except PlaywrightError as exc:
            target = "root element" if selector is None else selector
            raise BrowserAccessError(
                f"Failed to read DOM element text: {target}"
            ) from exc


class PlaywrightBrowserAccess(BrowserAccess):
    def __init__(self, context: BrowserContext):
        self._context: BrowserContext = context
        self._page: Page | None = None

    def open_url(
        self,
        url: str,
        *,
        wait_for_selectors: SelectorList = (),
        click_if_visible_selectors: SelectorList = (),
    ) -> None:
        page = self._get_page()

        try:
            clicked_selectors = open_and_prepare_page(
                page,
                url,
                wait_for=wait_for_selectors,
                click_if_visible_selectors=click_if_visible_selectors,
            )
        except PlaywrightError as exc:
            raise BrowserAccessError(f"Failed to open browser URL: {url}") from exc

        if clicked_selectors:
            log(f"clicked visible browser setup selectors: {clicked_selectors}")


    def download_page(self, url: str) -> str:
        page = self._get_page()

        try:
            open_page(page, url)
            return page.content()
        except PlaywrightError as exc:
            raise BrowserAccessError(f"Failed to download browser page: {url}") from exc


    def find_elements(self, selector: Selector) -> list[DOMElement]:
        try:
            locator = self._get_page().locator(selector)
            return [
                PlaywrightDOMElement(locator.nth(index))
                for index in range(locator.count())
            ]
        except PlaywrightError as exc:
            raise BrowserAccessError(
                f"Failed to find browser elements: {selector}"
            ) from exc


    def current_url(self) -> str:
        return self._get_page().url


    def _get_page(self) -> Page:
        if self._page is None:
            try:
                self._page = self._context.new_page()
            except PlaywrightError as exc:
                raise BrowserAccessError("Failed to create browser page") from exc

        return self._page


@contextmanager
def create_playwright_browser_access() -> Iterator[PlaywrightBrowserAccess]:
    with create_browser() as browser:
        with browser.new_context() as context:
            yield PlaywrightBrowserAccess(context=context)
