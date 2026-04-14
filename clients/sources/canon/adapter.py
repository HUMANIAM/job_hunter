from __future__ import annotations

import re
import sys
from typing import Any, List
from urllib.parse import urljoin

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log


CANON_ENTRY_URL = (
    "https://jobs.cpp.canon/search/"
    "?locale=en_GB&optionsFacetsDD_customfield3=Professional&searchResultView=LIST"
)
CANON_RESULTS_READY_SELECTORS = [
    "a[data-testid^='jobCardTitle_'][href]",
    "[data-testid='jobCardLocation']",
]

CANON_JOB_URL_RE = re.compile(
    r"^https://jobs\.cpp\.canon/job/[^/?#]+/\d+-en_GB/?$"
)


class CanonClientAdapter(BaseClientAdapter):
    ENTRY_URL = CANON_ENTRY_URL

    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> List[str]:
        limit = sys.maxsize if job_limit is None else job_limit
        return self._collect_job_links_via_listing(browser, job_limit=limit)

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

        links = page.locator("a[data-testid^='jobCardTitle_'][href]")
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

    def _get_next_page_url(self, page: Any) -> str | None:
        next_selectors = [
            "button[aria-label='next page']",
            "button[aria-label='Next']",
            "a[aria-label='Next']",
        ]

        for selector in next_selectors:
            try:
                element = page.locator(selector).first
                if element.count() == 0:
                    continue

                href = element.get_attribute("href")
                if href:
                    return urljoin(page.url, href)

                tag_name = element.evaluate("(el) => el.tagName.toLowerCase()")
                if tag_name == "button":
                    return "__CLICK_NEXT__"
            except Exception:
                continue

        return None

    def _click_next_page(self, page: Any) -> bool:
        next_selectors = [
            "button[aria-label='next page']",
            "button[aria-label='Next']",
            "a[aria-label='Next']",
        ]

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

    def _page_state_key(self, page: Any) -> str:
        hrefs: list[str] = []
        links = page.locator("a[data-testid^='jobCardTitle_'][href]")

        for index in range(links.count()):
            href = links.nth(index).get_attribute("href")
            if href:
                hrefs.append(urljoin(page.url, href))

        return "|".join(sorted(hrefs))

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        collected_links: set[str] = set()
        visited_page_keys: set[str] = set()
        page_index = 1

        while True:
            current_url = page.url
            page_links = self._collect_job_links_from_page(
                page,
                f"{context} page {page_index}",
                job_limit=job_limit - len(collected_links),
            )

            page_key = f"{current_url}::{self._page_state_key(page)}"
            if page_key in visited_page_keys:
                log(f"{context}: detected repeated page state, stopping")
                break

            visited_page_keys.add(page_key)

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

            next_page = self._get_next_page_url(page)
            if not next_page:
                log(f"{context}: no next page control")
                break

            if next_page == "__CLICK_NEXT__":
                log(f"{context}: clicking next page")
                moved = self._click_next_page(page)
                if not moved:
                    log(f"{context}: next page control not usable")
                    break
            else:
                log(f"{context}: following next page -> {next_page}")
                self._open_page(page, next_page)

            page_index += 1

        return collected_links

    def _collect_job_links_via_listing(
        self,
        browser: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        with browser.new_context() as context:
            page = context.new_page()
            self._open_page(page, self.ENTRY_URL)

            hrefs = self._collect_links_from_paginated_listing(
                page,
                context="canon nl listing",
                job_limit=job_limit,
            )

            log(f"canon nl listing: collected {len(hrefs)} unique job links")
            return sorted(hrefs)
