from __future__ import annotations

import re
from typing import Any, List
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log


CANON_ENTRY_URL = (
    "https://jobs.cpp.canon/search/"
    "?locale=en_GB&optionsFacetsDD_customfield3=Professional"
    "&searchResultView=LIST&markerViewed&carouselIndex&pageNumber=0"
    "&facetFilters=%7B%22jobType%22%3A%5B%22Professional%22%5D%2C"
    "%22sfstd_jobLocation_obj%22%3A%5B%22Venlo%22%5D%7D"
)
CANON_RESULTS_READY_SELECTORS = [
    "a[data-testid^='jobCardTitle_'][href]",
    "[data-testid='jobCardLocation']",
]
CANON_JOB_CARD_SELECTOR = "a[data-testid^='jobCardTitle_'][href]"

CANON_JOB_URL_RE = re.compile(
    r"^https://jobs\.cpp\.canon/job/[^/?#]+/\d+-en_GB/?$"
)


class CanonClientAdapter(BaseClientAdapter):
    ENTRY_URL = CANON_ENTRY_URL

    def _collect_job_links_in_context(
        self,
        context: Any,
        page: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        hrefs = self._collect_links_from_paginated_listing(
            page,
            context="canon nl listing",
            job_limit=job_limit,
        )

        log(f"canon nl listing: collected {len(hrefs)} unique job links")
        return sorted(hrefs)

    def _open_page(self, page: Any, url: str) -> None:
        clicked_selectors = open_and_prepare_page(
            page,
            url,
            wait_for=CANON_RESULTS_READY_SELECTORS,
        )

        if clicked_selectors:
            log(f"accepted cookie banner selectors: {clicked_selectors}")

        log(f"current page url: {page.url}")

    def _is_job_url(self, url: str) -> bool:
        return bool(CANON_JOB_URL_RE.match(url))

    def _collect_job_links_from_page(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        hrefs: set[str] = set()

        links = page.locator(CANON_JOB_CARD_SELECTOR)
        count = links.count()
        log(f"{context}: found {count} vacancy cards")

        for index in range(count):
            link = links.nth(index)
            href = link.get_attribute("href")
            if not href:
                continue

            location = ""
            try:
                card = link.locator("xpath=ancestor::li[@data-testid='jobCard']").first
                if card.count() > 0:
                    location = " ".join(
                        card.locator("[data-testid='jobCardLocation']").inner_text().split()
                    )
            except Exception:
                location = ""

            if "Netherlands" not in location:
                continue

            full_url = urljoin(page.url, href)
            if not self._is_job_url(full_url):
                continue

            hrefs.add(full_url)
            if len(hrefs) >= job_limit:
                break

        log(f"{context}: collected {len(hrefs)} job links from current page")
        return hrefs

    def _page_card_count(self, page: Any) -> int:
        return page.locator(CANON_JOB_CARD_SELECTOR).count()

    def _build_page_url(self, page_number: int) -> str:
        parsed = urlparse(self.ENTRY_URL)
        query_items = parse_qsl(parsed.query, keep_blank_values=True)
        updated_items: list[tuple[str, str]] = []
        replaced = False

        for key, value in query_items:
            if key == "pageNumber":
                updated_items.append((key, str(page_number)))
                replaced = True
            else:
                updated_items.append((key, value))

        if not replaced:
            updated_items.append(("pageNumber", str(page_number)))

        return urlunparse(parsed._replace(query=urlencode(updated_items, doseq=True)))

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        collected_links: set[str] = set()
        page_number = 0

        while True:
            page_url = self._build_page_url(page_number)
            self._open_page(page, page_url)

            page_index = page_number + 1
            page_links = self._collect_job_links_from_page(
                page,
                f"{context} page {page_index}",
                job_limit=job_limit - len(collected_links),
            )
            card_count = self._page_card_count(page)

            if card_count == 0:
                log(f"{context} page {page_index}: empty page, stopping")
                break

            before = len(collected_links)
            collected_links.update(page_links)
            after = len(collected_links)

            log(
                f"{context} page {page_index}: "
                f"added {after - before} new links | cumulative={after}"
            )

            if len(collected_links) >= job_limit:
                log(f"{context}: reached job limit, stopping")
                break

            page_number += 1

        return collected_links
