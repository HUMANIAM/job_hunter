from __future__ import annotations

import re
from typing import Any, List
from urllib.parse import urljoin

from clients.sources.browser_listing_adapter import (
    BrowserListingAdapter,
    PageAdvance,
)
from infra.logging import log


ASML_ENTRY_URL = (
    "https://www.asml.com/en/careers/find-your-job"
    "?job_country=Netherlands&job_type=Fix"
)

ASML_RESULTS_READY_SELECTORS = [
    "a[href*='/careers/find-your-job/']",
    "a[href*='myworkdayjobs.com']",
]

ASML_COOKIE_ACCEPT_SELECTORS = [
    "#onetrust-accept-btn-handler",
]

ASML_JOB_URL_RE = re.compile(
    r"^https://www\.asml\.com/en/careers/find-your-job/[^/?#]+$"
)

# Optional fallback if ASML links directly to Workday-hosted jobs.
ASML_WORKDAY_JOB_URL_RE = re.compile(
    r"^https://[^/]*myworkdayjobs\.com/[^/]+/job/[^?#]+$"
)


class AsmlClientAdapter(BrowserListingAdapter):
    entry_url = ASML_ENTRY_URL
    listing_label = "asml nl listing"
    results_ready_selectors = tuple(ASML_RESULTS_READY_SELECTORS)
    cookie_accept_selectors = tuple(ASML_COOKIE_ACCEPT_SELECTORS)

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        page = context.new_page()
        self._open_page(page, self.entry_url)
        hrefs = super()._collect_links_from_paginated_listing(
            page,
            self.listing_label,
            job_limit=job_limit,
        )

        log(f"{self.listing_label}: collected {len(hrefs)} unique job links")
        return sorted(hrefs)

    def _is_job_url(self, url: str) -> bool:
        return bool(
            ASML_JOB_URL_RE.match(url)
            or ASML_WORKDAY_JOB_URL_RE.match(url)
        )

    def _get_job_links_from_page(
        self,
        page: Any,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return self._collect_job_links_from_page_common(
            page,
            log_context=log_context,
            job_limit=job_limit,
            candidates_selector="a[href]",
            found_label="anchor elements",
            normalize_href=lambda href: urljoin(page.url, href),
            is_job_url=self._is_job_url,
        )

    def _get_page_advance(self, page: Any) -> PageAdvance:
        return self._get_page_advance_common(
            page,
            next_selectors=(
                "button[aria-label='next']",
                "a[aria-label='Next']",
                "a[rel='next']",
                "a.pagination__next",
                "button[aria-label='Next']",
            ),
            normalize_next_href=lambda href: urljoin(page.url, href),
            is_click_next_control=lambda element: (
                element.evaluate("(el) => el.tagName.toLowerCase()") == "button"
            ),
        )

    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        return self._get_next_page_common(
            page,
            page_advance,
            click_next_page=self._click_next_page,
        )

    def _click_next_page(self, page: Any) -> bool:
        next_selectors = (
            "button[aria-label='next']",
            "button[aria-label='Next']",
            "a[aria-label='Next']",
            "a.pagination__next",
        )

        for selector in next_selectors:
            try:
                element = page.locator(selector).first
                if element.count() == 0:
                    continue

                disabled = element.get_attribute("disabled")
                aria_disabled = element.get_attribute("aria-disabled")
                class_name = element.get_attribute("class") or ""

                if (
                    disabled is not None
                    or aria_disabled == "true"
                    or "disabled" in class_name.lower()
                ):
                    return False

                element.click()
                page.wait_for_timeout(1500)
                return True
            except Exception as exc:
                log(
                    f"{self.listing_label}: selector '{selector}' click raised "
                    f"{exc.__class__.__name__}: {exc}"
                )
                continue

        return False
