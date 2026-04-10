from __future__ import annotations

import re
import sys
from typing import Any, List
from urllib.parse import urljoin

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log
from shared.normalizer import normalize_text


SIOUX_ENTRY_URL = "https://vacancy.sioux.eu/"
SIOUX_RESULTS_READY_SELECTOR = "a.act-item-job-overview"
SIOUX_COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"
SIOUX_JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")


class SiouxClientAdapter(BaseClientAdapter):
    ENTRY_URL = SIOUX_ENTRY_URL

    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> List[str]:
        limit = sys.maxsize if job_limit is None else job_limit
        return self._collect_job_links_via_facets(browser, job_limit=limit)


    def _open_page(self, page: Any, url: str) -> None:
        clicked_selectors = open_and_prepare_page(
            page,
            url,
            wait_for=[SIOUX_RESULTS_READY_SELECTOR],
            click_if_visible_selectors=[SIOUX_COOKIE_ACCEPT_SELECTOR],
        )
        if SIOUX_COOKIE_ACCEPT_SELECTOR in clicked_selectors:
            log("accepted cookie banner")

        log(f"current page url: {page.url}")


    def _extract_discipline_facets(self, page: Any) -> List[tuple[str, str, int]]:
        facets: List[tuple[str, str, int]] = []

        links = page.locator("div.facets_item[data-type='functiegr'] a.filter-item-link")
        count = links.count()
        log(f"found {count} discipline facet links")

        for index in range(count):
            link = links.nth(index)
            name = normalize_text(link.locator(".filter-item-link-name").inner_text())
            count_text = normalize_text(link.locator(".filter-item-link-count").inner_text())
            href = link.get_attribute("href")
            if not href:
                continue

            expected_count = int(count_text) if count_text.isdigit() else -1
            full_url = urljoin(self.ENTRY_URL, href)
            facets.append((name, full_url, expected_count))
            log(f"facet: name='{name}' expected={expected_count} url={full_url}")

        return facets

    def _collect_job_links_from_page(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        hrefs: set[str] = set()

        cards = page.locator("a.act-item-job-overview")
        count = cards.count()
        log(f"{context}: found {count} vacancy cards")

        for index in range(count):
            href = cards.nth(index).get_attribute("href")
            if not href:
                continue

            full_url = urljoin(self.ENTRY_URL, href)
            if SIOUX_JOB_URL_RE.match(full_url):
                hrefs.add(full_url)
                if len(hrefs) >= job_limit:
                    break

        log(f"{context}: collected {len(hrefs)} vacancy links from current page")
        return hrefs

    def _get_next_page_url(self, page: Any) -> str | None:
        try:
            next_link = page.locator(
                "div.overview-paging-controls a.paging-item-next"
            ).first
            if next_link.count() == 0:
                return None

            href = next_link.get_attribute("href")
            if not href:
                return None

            return urljoin(self.ENTRY_URL, href)
        except Exception:
            return None

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        expected_count: int | None = None,
        *,
        job_limit: int,
    ) -> set[str]:
        collected_links: set[str] = set()
        visited_pages: set[str] = set()
        page_index = 1

        while True:
            current_url = page.url
            if current_url in visited_pages:
                log(f"{context}: detected repeated page url, skipping")
            else:
                visited_pages.add(current_url)

                if len(collected_links) >= job_limit:
                    log(f"{context}: reached job limit, stopping pagination")
                    break

                page_links = self._collect_job_links_from_page(
                    page,
                    f"{context} page {page_index}",
                    job_limit=job_limit - len(collected_links),
                )
                before = len(collected_links)
                collected_links.update(page_links)
                after = len(collected_links)

                log(
                    f"{context} page {page_index}: "
                    f"added {after - before} new links | cumulative={after}"
                )

                if expected_count is not None and expected_count > 0 and after >= expected_count:
                    log(f"{context}: reached expected count, stopping pagination")
                    break

                if len(collected_links) >= job_limit:
                    log(f"{context}: reached job limit, stopping pagination")
                    break

            next_url = self._get_next_page_url(page)
            if not next_url:
                log(f"{context}: no next page link")
                break

            if next_url in visited_pages:
                log(f"{context}: next page url already visited, stopping")
                break

            log(f"{context}: following next page -> {next_url}")
            self._open_page(page, next_url)
            page_index += 1

        return collected_links


    def _collect_links_for_facet(
        self,
        context: Any,
        facet_name: str,
        facet_url: str,
        expected_count: int,
        *,
        job_limit: int,
    ) -> set[str]:
        page = context.new_page()

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


    def _collect_job_links_via_facets(
        self,
        browser: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        all_hrefs: set[str] = set()

        # collect discipline facets from the entry page
        with browser.new_context() as context:
            page = context.new_page()
            self._open_page(page, self.ENTRY_URL)
            facets = self._extract_discipline_facets(page)
            log(f"collected {len(facets)} discipline facets")


            # collect job links from each facet
            for facet_name, facet_url, expected_count in facets:
                if len(all_hrefs) >= job_limit:
                    log("facet traversal: reached job limit, stopping")
                    break

                log(f"--- facet traversal: {facet_name} ---")
                facet_links = self._collect_links_for_facet(
                    context,
                    facet_name,
                    facet_url,
                    expected_count,
                    job_limit=job_limit - len(all_hrefs),
                )

                all_hrefs.update(facet_links)

            return sorted(all_hrefs)
