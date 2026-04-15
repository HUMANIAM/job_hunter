from __future__ import annotations

import re
from typing import Any, List
from urllib.parse import urljoin

from clients.sources.browser_listing_adapter import (
    BrowserListingAdapter,
    PageAdvance,
)
from clients.sources.vanderlande.job_html import render_vanderlande_job_html
from infra.logging import log


# NL + Regular contract
VANDERLANDE_ENTRY_URL = (
    "https://vanderlande.wd3.myworkdayjobs.com/en-US/careers"
    "?locationCountry=9696868b09c64d52a62ee13b052383cc"
    "&workerSubType=65d289099a0c104a3602035a812e138b"
)

VANDERLANDE_RESULTS_READY_SELECTORS = [
    "a[data-automation-id='jobTitle'][href]",
    "a[href*='/job/']",
]

VANDERLANDE_JOB_URL_RE = re.compile(
    r"^https://vanderlande\.wd3\.myworkdayjobs\.com/en-US/careers/job/[^?#]+$"
)


class VanderlandeClientAdapter(BrowserListingAdapter):
    entry_url = VANDERLANDE_ENTRY_URL
    listing_label = "vanderlande nl listing"
    results_ready_selectors = tuple(VANDERLANDE_RESULTS_READY_SELECTORS)

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        page = context.new_page()
        self._open_page(page, self.entry_url)
        hrefs = self._collect_links_from_paginated_listing(
            page,
            self.listing_label,
            job_limit=job_limit,
        )

        log(f"vanderlande nl listing: collected {len(hrefs)} unique job links")
        return sorted(hrefs)

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        expected_count: int | None = None,
        *,
        job_limit: int,
    ) -> set[str]:
        return super()._collect_links_from_paginated_listing(
            page,
            context,
            expected_count,
            job_limit=job_limit,
        )

    def transform_downloaded_html(
        self,
        *,
        url: str,
        title: str | None,
        html_content: str,
    ) -> tuple[str | None, str]:
        rendered = render_vanderlande_job_html(html_content)
        if rendered is None:
            return title, html_content

        transformed_title, transformed_html = rendered
        return transformed_title or title, transformed_html

    def _is_job_url(self, url: str) -> bool:
        return bool(VANDERLANDE_JOB_URL_RE.match(url))

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
            candidates_selector="a[data-automation-id='jobTitle'][href]",
            found_label="vacancy links",
            normalize_href=lambda href: urljoin(page.url, href).split("?", 1)[0],
            is_job_url=self._is_job_url,
        )

    def _get_page_advance(self, page: Any) -> PageAdvance:
        return self._get_page_advance_common(
            page,
            next_selectors=(
                "button[aria-label='next']",
                "button[data-uxi-element-id='next']",
                "button[aria-label='Next']",
                "a[aria-label='Next']",
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
            "button[data-uxi-element-id='next']",
            "button[aria-label='Next']",
            "a[aria-label='Next']",
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
            except Exception:
                continue

        return False

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return super()._collect_links_from_paginated_listing(
            page,
            context,
            job_limit=job_limit,
        )
