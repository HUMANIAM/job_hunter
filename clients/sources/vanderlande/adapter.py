from __future__ import annotations

import re
import sys
from typing import Any, List
from urllib.parse import urljoin

from clients.base import BaseClientAdapter
from clients.sources.vanderlande.job_html import render_vanderlande_job_html
from infra.browser import open_and_prepare_page
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


class VanderlandeClientAdapter(BaseClientAdapter):
    ENTRY_URL = VANDERLANDE_ENTRY_URL

    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> List[str]:
        limit = sys.maxsize if job_limit is None else job_limit
        return self._collect_job_links_via_listing(browser, job_limit=limit)

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

    def _open_page(self, page: Any, url: str) -> None:
        open_and_prepare_page(
            page,
            url,
            wait_for=VANDERLANDE_RESULTS_READY_SELECTORS,
        )
        log(f"current page url: {page.url}")

    def _is_job_url(self, url: str) -> bool:
        return bool(VANDERLANDE_JOB_URL_RE.match(url))

    def _collect_job_links_from_page(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        hrefs: set[str] = set()

        links = page.locator("a[data-automation-id='jobTitle'][href]")
        count = links.count()
        log(f"{context}: found {count} vacancy links")

        for index in range(count):
            href = links.nth(index).get_attribute("href")
            if not href:
                continue

            full_url = urljoin(page.url, href).split("?", 1)[0]
            if not self._is_job_url(full_url):
                continue

            hrefs.add(full_url)
            if len(hrefs) >= job_limit:
                break

        log(f"{context}: collected {len(hrefs)} job links from current page")
        return hrefs

    def _get_next_page_url(self, page: Any) -> str | None:
        next_selectors = [
            "button[aria-label='next']",
            "button[data-uxi-element-id='next']",
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
            "button[aria-label='next']",
            "button[data-uxi-element-id='next']",
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

            page_key = f"{current_url}::{'|'.join(sorted(page_links))}"
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
                context="vanderlande nl listing",
                job_limit=job_limit,
            )

            log(f"vanderlande nl listing: collected {len(hrefs)} unique job links")
            return sorted(hrefs)
