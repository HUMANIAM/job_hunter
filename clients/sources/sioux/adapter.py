from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from clients.sources.browser_listing_adapter import (
    BrowserListingAdapter,
    PageAdvance,
)
from infra.logging import log
from shared.normalizer import normalize_text


SIOUX_ENTRY_URL = "https://vacancy.sioux.eu/"
SIOUX_RESULTS_READY_SELECTOR = "a.act-item-job-overview"
SIOUX_COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"
SIOUX_JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")
SIOUX_DISCIPLINE_FACET_SELECTOR = (
    "div.facets_item[data-type='functiegr'] a.filter-item-link"
)


class SiouxBrowserListingAdapter(BrowserListingAdapter):
    """Typed placeholder for the Sioux browser-listing refactor."""

    entry_url = SIOUX_ENTRY_URL
    listing_label = "sioux listing"
    results_ready_selectors = (SIOUX_RESULTS_READY_SELECTOR,)
    cookie_accept_selectors = (SIOUX_COOKIE_ACCEPT_SELECTOR,)

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> list[str]:
        page = context.new_page()
        self._open_page(page, self.entry_url)

        facets = self._extract_discipline_facets(page)
        log(f"collected {len(facets)} discipline facets")

        all_hrefs: set[str] = set()
        for facet_name, facet_url, expected_count in facets:
            if len(all_hrefs) >= job_limit:
                log("facet traversal: reached job limit, stopping")
                break

            log(f"--- facet traversal: {facet_name} ---")
            facet_links = self._collect_links_for_facet(
                page,
                facet_name,
                facet_url,
                expected_count,
                job_limit=job_limit - len(all_hrefs),
            )
            all_hrefs.update(facet_links)

        return sorted(all_hrefs)

    def _extract_discipline_facets(self, page: Any) -> list[tuple[str, str, int]]:
        facets: list[tuple[str, str, int]] = []

        links = page.locator(SIOUX_DISCIPLINE_FACET_SELECTOR)
        count = links.count()

        for index in range(count):
            link = links.nth(index)
            name = normalize_text(link.locator(".filter-item-link-name").inner_text())
            count_text = normalize_text(
                link.locator(".filter-item-link-count").inner_text()
            )
            href = link.get_attribute("href")
            if not href:
                continue

            expected_count = int(count_text) if count_text.isdigit() else -1
            facets.append((name, urljoin(self.entry_url, href), expected_count))

        return facets


    def _collect_links_for_facet(
        self,
        page: Any,
        facet_name: str,
        facet_url: str,
        expected_count: int,
        *,
        job_limit: int,
    ) -> set[str]:
        log(f"facet '{facet_name}': opening facet page")
        self._open_page(page, facet_url)

        facet_links = self._collect_links_from_paginated_listing(
            page,
            context=f"facet '{facet_name}'",
            expected_count=expected_count,
            job_limit=job_limit,
        )

        log(
            f"facet '{facet_name}': collected {len(facet_links)} unique links "
            f"(sidebar expected count={expected_count})"
        )
        return facet_links

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
            candidates_selector="a.act-item-job-overview",
            found_label="vacancy cards",
            normalize_href=lambda href: urljoin(self.entry_url, href),
            is_job_url=lambda url: bool(SIOUX_JOB_URL_RE.match(url)),
        )

    def _get_page_advance(self, page: Any) -> PageAdvance:
        return self._get_page_advance_common(
            page,
            next_selectors=("div.overview-paging-controls a.paging-item-next",),
            normalize_next_href=lambda href: urljoin(self.entry_url, href),
            is_click_next_control=lambda _element: False,
        )

    def _get_next_page(self, page: Any, page_advance: PageAdvance) -> Any:
        return self._get_next_page_common(page, page_advance)
