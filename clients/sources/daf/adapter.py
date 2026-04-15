from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from clients.sources.browser_listing_adapter import (
    BrowserListingAdapter,
    PageAdvance,
)
from infra.logging import log


DAF_ENTRY_URL = (
    "https://www.daf.com/en/working-at-daf/vacancies"
    "?Page=1&functionlevel=Professionals&region=Netherlands"
)

DAF_RESULTS_READY_SELECTORS = [
    "a.vacancy-item__link[href]",
    "a.js-vac-title[href]",
]

DAF_COOKIE_ACCEPT_SELECTORS = [
    "#onetrust-accept-btn-handler",
]

DAF_JOB_URL_RE = re.compile(
    r"^https://www\.daf\.com/en/working-at-daf/vacancies/"
    r"(?!job-alert$|application-procedure$|open-application$)"
    r"[^/?#]+$"
)


class DafClientAdapter(BrowserListingAdapter):
    entry_url = DAF_ENTRY_URL
    listing_label = "daf nl professionals listing"
    results_ready_selectors = tuple(DAF_RESULTS_READY_SELECTORS)
    cookie_accept_selectors = tuple(DAF_COOKIE_ACCEPT_SELECTORS)
    ENTRY_URL = DAF_ENTRY_URL

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> list[str]:
        page = context.new_page()
        self._open_page(page, self.entry_url)
        hrefs = super()._collect_links_from_paginated_listing(
            page,
            context=self.listing_label,
            job_limit=job_limit,
        )

        log(f"{self.listing_label}: collected {len(hrefs)} unique job links")
        return sorted(hrefs)

    def _is_job_url(self, url: str) -> bool:
        return bool(DAF_JOB_URL_RE.match(url))

    def _get_job_links_from_page(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return self._collect_job_links_from_page_common(
            page,
            log_context=context,
            job_limit=job_limit,
            candidates_selector="a.vacancy-item__link[href]",
            found_label="vacancy links",
            normalize_href=lambda href: urljoin(page.url, href),
            is_job_url=self._is_job_url,
        )

    def _get_page_advance(self, page: Any) -> PageAdvance:
        return self._get_page_advance_common(
            page,
            next_selectors=("a.page-link.page-link--next",),
            normalize_next_href=lambda href: urljoin(page.url, href),
            is_click_next_control=self._is_click_next_control,
        )

    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        return self._get_next_page_common(
            page,
            page_advance,
            click_next_page=self._click_next_page,
        )

    def _is_click_next_control(self, element: Any) -> bool:
        data_page = element.get_attribute("data-page")
        if data_page != "next":
            return False

        disabled = element.get_attribute("disabled")
        aria_disabled = element.get_attribute("aria-disabled")
        class_name = element.get_attribute("class") or ""

        return not (
            disabled is not None
            or aria_disabled == "true"
            or "disabled" in class_name.lower()
        )

    def _click_next_page(self, page: Any) -> bool:
        element = page.locator("a.page-link.page-link--next").first
        if element.count() == 0:
            return False

        if not self._is_click_next_control(element):
            return False

        try:
            element.click()
            page.wait_for_timeout(1500)
            return True
        except Exception:
            return False
