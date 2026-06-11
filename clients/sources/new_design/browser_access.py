from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

Selector = str
SelectorList = Sequence[Selector]


class BrowserAccessError(RuntimeError):
    """Raised when a browser access implementation cannot complete an operation."""


class DOMElement(ABC):
    @abstractmethod
    def get_attribute(self, name: str) -> str | None:
        """Get the value of the specified attribute of the element."""
        pass

    @abstractmethod
    def get_text(self, selector: str | None = None) -> str:
        """Get the text content of the element, or of a child element specified by the selector."""
        pass


class BrowserAccess(ABC):
    @abstractmethod
    def open_url(
        self,
        url: str,
        *,
        wait_for_selectors: SelectorList = (),
        click_if_visible_selectors: SelectorList = (),
    ) -> None:
        """
        Open the specified URL in a web browser.
        Args:
            url: The URL to open.
            wait_for_selectors: Selectors to wait for after opening the URL.
            click_if_visible_selectors: Selectors to click when visible.
        """
        pass

    @abstractmethod
    def download_page(self, url: str) -> str:
        """
        Open the specified URL and return the loaded page HTML.
        Args:
            url: The URL to download.
        Returns:
            The current page HTML.
        """
        pass

    @abstractmethod
    def find_elements(self, selector: Selector) -> list[DOMElement]:
        """
        Find DOM elements matching the selector on the current browser page.
        Args:
            selector: The selector to query.
        Returns:
            Matching DOM elements from the current page.
        """
        pass

    @abstractmethod
    def current_url(self) -> str:
        """
        Get the current browser page URL.
        Returns:
            The current URL of the active browser page.
        """
        pass
