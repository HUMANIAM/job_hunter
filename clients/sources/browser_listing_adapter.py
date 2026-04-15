from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Sequence

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log


class AdvanceDecision(str, Enum):
    """How a browser listing should advance after processing the current page."""

    FOLLOW_URL = "follow_url"
    CLICK = "click"
    STOP = "stop"


@dataclass(frozen=True)
class PageAdvance:
    """The pagination instruction for the current browser listing page."""

    advance_decision: AdvanceDecision
    next_page_url: str | None = None


class BrowserListingAdapter(BaseClientAdapter, ABC):
    """Contract for client adapters that collect job links from browser DOM pages.

    This is a browser-listing-specific adapter contract, not the global public
    adapter protocol. External callers should still use `collect_job_links(...)`.

    Subclasses are expected to:
    - provide the entry-point configuration for the listing surface
    - extract only the links visible on the current page
    - decide how pagination should advance from the current page
    - return the next listing URL together with the advance decision when needed
    - resolve that page-advance instruction into the next page object
    """

    entry_url: str
    listing_label: str
    results_ready_selectors: Sequence[str]
    cookie_accept_selectors: Sequence[str] = ()

    def _open_page(self, page: Any, url: str) -> None:
        """Open a listing page and apply the shared browser-listing preparation."""

        clicked_selectors = open_and_prepare_page(
            page,
            url,
            wait_for=self.results_ready_selectors,
            click_if_visible_selectors=self.cookie_accept_selectors,
        )
        if clicked_selectors:
            log(f"accepted cookie banner selectors: {clicked_selectors}")

        log(f"current page url: {page.url}")

    @abstractmethod
    def _get_job_links_from_page(
        self,
        page: Any,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        """Return only the job links visible on the current listing page."""
        raise NotImplementedError

    @abstractmethod
    def _get_page_advance(self, page: Any) -> PageAdvance:
        """Return the next pagination instruction for the current browser page.

        When `advance_decision` is `FOLLOW_URL`, `next_page_url` should contain
        the next listing URL. For `CLICK` and `STOP`, `next_page_url` should
        usually be `None`.
        """
        raise NotImplementedError

    @abstractmethod
    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        """Execute the page-advance instruction and return the next page object.

        Implementations should interpret `page_advance.advance_decision` and
        either navigate to `page_advance.next_page_url`, click the relevant next
        control, or reject invalid `STOP` inputs. The returned object is the
        page instance positioned on the next listing page.
        """
        raise NotImplementedError
