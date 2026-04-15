from __future__ import annotations

import re
from typing import Any, Callable, List, Sequence
from urllib.parse import urljoin

from clients.base import BaseClientAdapter
from clients.sources.browser_listing_adapter import AdvanceDecision, PageAdvance
from infra.browser import open_and_prepare_page
from infra.logging import log
from shared.normalizer import normalize_text


SIOUX_ENTRY_URL = "https://vacancy.sioux.eu/"
SIOUX_RESULTS_READY_SELECTOR = "a.act-item-job-overview"
SIOUX_COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"
SIOUX_JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")

def _collect_job_links_from_page_common(
    self,
    page: Any,
    *,
    log_context: str,
    job_limit: int,
    candidates_selector: str,
    found_label: str,
    normalize_href: Callable[[str], str | None],
    is_job_url: Callable[[str], bool],
) -> set[str]:
    hrefs: set[str] = set()

    links = page.locator(candidates_selector)
    count = links.count()
    log(f"{log_context}: found {count} {found_label}")

    for index in range(count):
        href = links.nth(index).get_attribute("href")
        if not href:
            continue

        full_url = normalize_href(href)
        if not full_url or not is_job_url(full_url):
            continue

        hrefs.add(full_url)
        if len(hrefs) >= job_limit:
            break

    log(f"{log_context}: collected {len(hrefs)} job links from current page")
    return hrefs


def _get_page_advance_common(
    self,
    page: Any,
    *,
    next_selectors: Sequence[str],
    normalize_next_href: Callable[[str], str | None],
    is_click_next_control: Callable[[Any], bool],
) -> PageAdvance:
    for selector in next_selectors:
        try:
            element = page.locator(selector).first
            if element.count() == 0:
                continue

            href = element.get_attribute("href")
            if href:
                next_page_url = normalize_next_href(href)
                if next_page_url:
                    res = PageAdvance(advance_decision=AdvanceDecision.FOLLOW_URL,
                                    next_page_url=next_page_url,)
                    return res

            if is_click_next_control(element):
                return PageAdvance(advance_decision=AdvanceDecision.CLICK)
        except Exception as exc:
            log(
                f"next page detection: selector '{selector}' raised "
                f"{exc.__class__.__name__}: {exc}"
            )
            continue

    return PageAdvance(advance_decision=AdvanceDecision.STOP)


class SiouxClientAdapter(BaseClientAdapter):
    ENTRY_URL = SIOUX_ENTRY_URL

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        page = context.new_page()
        self._open_page(page, self.ENTRY_URL)

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
        return _collect_job_links_from_page_common(
            self,
            page,
            log_context=context,
            job_limit=job_limit,
            candidates_selector="a.act-item-job-overview",
            found_label="vacancy cards",
            normalize_href=lambda href: urljoin(self.ENTRY_URL, href),
            is_job_url=lambda url: bool(SIOUX_JOB_URL_RE.match(url)),
        )

    def _get_next_page_url(self, page: Any) -> str | None:
        page_advance = _get_page_advance_common(
            self,
            page,
            next_selectors=("div.overview-paging-controls a.paging-item-next",),
            normalize_next_href=lambda href: urljoin(self.ENTRY_URL, href),
            is_click_next_control=lambda _element: False,
        )
        if page_advance.advance_decision != AdvanceDecision.FOLLOW_URL:
            return None

        return page_advance.next_page_url

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
