#!/usr/bin/env python3
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable

from infra.browser import click_if_visible, wait_for_page_ready
from infra.logging import log
from playwright.sync_api import Browser, Page
from shared.normalizer import normalize_text

START_URL = "https://vacancy.sioux.eu/"
BASE_URL = "https://vacancy.sioux.eu"
RESULTS_READY_SELECTOR = "a.act-item-job-overview"
COOKIE_ACCEPT_SELECTOR = "input.cookieClose.cookieAccept"

# Reserved for future parsing-based filtering once structured fields are reliable.
TARGET_COUNTRIES: tuple[str, ...] = ()
TARGET_LANGUAGES: tuple[str, ...] = ()

JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")


@dataclass
class SiouxRetrievalResult:
    job_links: list[str]
    discipline_map: dict[str, list[str]]
    validation_report: dict[str, object]


def absolutize_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href.lstrip("/")


def extract_discipline_facets(page: Page) -> list[tuple[str, str, int]]:
    facets: list[tuple[str, str, int]] = []

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
        full_url = absolutize_url(href)
        facets.append((name, full_url, expected_count))
        log(f"facet: name='{name}' expected={expected_count} url={full_url}")

    return facets


def collect_job_links_from_page(
    page: Page,
    context: str,
    *,
    job_limit: int | None = None,
) -> set[str]:
    hrefs: set[str] = set()

    cards = page.locator("a.act-item-job-overview")
    count = cards.count()
    log(f"{context}: found {count} vacancy cards")

    for index in range(count):
        href = cards.nth(index).get_attribute("href")
        if not href:
            continue
        href = absolutize_url(href)
        if JOB_URL_RE.match(href):
            hrefs.add(href)
            if job_limit is not None and len(hrefs) >= job_limit:
                break

    log(f"{context}: collected {len(hrefs)} vacancy links from current page")
    return hrefs


def collect_links_from_paginated_listing(
    page: Page,
    context: str,
    expected_count: int | None = None,
    job_limit: int | None = None,
) -> set[str]:
    collected_links: set[str] = set()
    visited_pages: set[str] = set()
    page_index = 1

    while True:
        current_url = page.url
        if current_url in visited_pages:
            log(f"{context}: detected repeated page url, stopping")
            break

        visited_pages.add(current_url)

        remaining_limit = None
        if job_limit is not None:
            remaining_limit = max(job_limit - len(collected_links), 0)
            if remaining_limit == 0:
                log(f"{context}: reached job limit, stopping pagination")
                break

        page_links = collect_job_links_from_page(
            page,
            f"{context} page {page_index}",
            job_limit=remaining_limit,
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

        if job_limit is not None and after >= job_limit:
            log(f"{context}: reached job limit, stopping pagination")
            break

        next_url = get_next_page_url(page)
        if not next_url:
            log(f"{context}: no next page link")
            break

        if next_url in visited_pages:
            log(f"{context}: next page url already visited, stopping")
            break

        log(f"{context}: following next page -> {next_url}")
        page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
        wait_for_page_ready(page, RESULTS_READY_SELECTOR)
        page_index += 1

    return collected_links


def get_next_page_url(page: Page) -> str | None:
    try:
        next_link = page.locator("div.overview-paging-controls a.paging-item-next").first
        if next_link.count() == 0:
            return None

        href = next_link.get_attribute("href")
        if not href:
            return None

        return absolutize_url(href)
    except Exception:
        return None


def collect_links_for_facet(
    browser: Browser,
    facet_name: str,
    facet_url: str,
    expected_count: int,
    *,
    job_limit: int | None = None,
) -> set[str]:
    context = browser.new_context()
    page = context.new_page()

    try:
        log(f"facet '{facet_name}': opening fresh session")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_page_ready(page, RESULTS_READY_SELECTOR)
        if click_if_visible(page, COOKIE_ACCEPT_SELECTOR):
            log("accepted cookie banner")

        log(f"facet '{facet_name}': opening facet url")
        page.goto(facet_url, wait_until="domcontentloaded", timeout=30000)
        wait_for_page_ready(page, RESULTS_READY_SELECTOR)

        facet_links = collect_links_from_paginated_listing(
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
    finally:
        context.close()


def collect_job_links_via_facets(
    browser: Browser,
    *,
    job_limit: int | None = None,
) -> tuple[list[str], dict[str, list[str]]]:
    seed_context = browser.new_context()
    seed_page = seed_context.new_page()

    try:
        log(f"opening entry page: {START_URL}")
        seed_page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_page_ready(seed_page, RESULTS_READY_SELECTOR)
        if click_if_visible(seed_page, COOKIE_ACCEPT_SELECTOR):
            log("accepted cookie banner")
        log(f"current page url: {seed_page.url}")

        facets = extract_discipline_facets(seed_page)
    finally:
        seed_context.close()

    all_hrefs: set[str] = set()
    url_to_disciplines: dict[str, set[str]] = {}

    for facet_name, facet_url, expected_count in facets:
        if job_limit is not None and len(all_hrefs) >= job_limit:
            log("facet traversal: reached job limit, stopping")
            break

        log(f"--- facet traversal: {facet_name} ---")
        remaining_limit = None
        if job_limit is not None:
            remaining_limit = max(job_limit - len(all_hrefs), 0)

        facet_links = collect_links_for_facet(
            browser,
            facet_name,
            facet_url,
            expected_count,
            job_limit=remaining_limit,
        )

        for url in sorted(facet_links):
            if job_limit is not None and url not in all_hrefs and len(all_hrefs) >= job_limit:
                break
            all_hrefs.add(url)
            url_to_disciplines.setdefault(url, set()).add(facet_name)

        log(
            f"facet '{facet_name}': merged into global set | "
            f"facet_links={len(facet_links)} | cumulative={len(all_hrefs)}"
        )

    job_links = sorted(all_hrefs)
    discipline_map = {
        url: sorted(disciplines)
        for url, disciplines in url_to_disciplines.items()
    }

    log(f"finished link collection: {len(job_links)} total unique vacancy links")
    for index, link in enumerate(job_links, start=1):
        log(f"link {index}: {link} | disciplines={discipline_map.get(link, [])}")

    return job_links, discipline_map


def collect_job_links_via_unfiltered_pagination(
    browser: Browser,
    *,
    job_limit: int | None = None,
) -> list[str]:
    context = browser.new_context()
    page = context.new_page()

    try:
        log(f"unfiltered overview: opening entry page: {START_URL}")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_page_ready(page, RESULTS_READY_SELECTOR)
        if click_if_visible(page, COOKIE_ACCEPT_SELECTOR):
            log("accepted cookie banner")
        log(f"unfiltered overview: current page url: {page.url}")

        unfiltered_links = collect_links_from_paginated_listing(
            page,
            context="unfiltered overview",
            job_limit=job_limit,
        )
        job_links = sorted(unfiltered_links)

        log(
            "unfiltered overview: finished link collection: "
            f"{len(job_links)} total unique vacancy links"
        )
        for index, link in enumerate(job_links, start=1):
            log(f"unfiltered overview link {index}: {link}")

        return job_links
    finally:
        context.close()


def build_collection_validation_report(
    facet_union_urls: Iterable[str],
    unfiltered_pagination_urls: Iterable[str],
) -> dict[str, object]:
    facet_union_set = set(facet_union_urls)
    unfiltered_pagination_set = set(unfiltered_pagination_urls)

    only_in_facet_union = sorted(facet_union_set - unfiltered_pagination_set)
    only_in_unfiltered_pagination = sorted(
        unfiltered_pagination_set - facet_union_set
    )

    return {
        "fetched_at_unix": int(time.time()),
        "source": START_URL,
        "configured_countries": list(TARGET_COUNTRIES),
        "configured_languages": list(TARGET_LANGUAGES),
        "facet_union_unique_count": len(facet_union_set),
        "unfiltered_pagination_unique_count": len(unfiltered_pagination_set),
        "facet_union_urls": sorted(facet_union_set),
        "unfiltered_pagination_urls": sorted(unfiltered_pagination_set),
        "only_in_facet_union_count": len(only_in_facet_union),
        "only_in_facet_union": only_in_facet_union,
        "only_in_unfiltered_pagination_count": len(only_in_unfiltered_pagination),
        "only_in_unfiltered_pagination": only_in_unfiltered_pagination,
        "sets_exactly_equal": facet_union_set == unfiltered_pagination_set,
    }


def log_collection_validation_report(report: dict[str, object]) -> None:
    log("collection validation report")
    log(f"facet_union_unique_count={report['facet_union_unique_count']}")
    log(
        "unfiltered_pagination_unique_count="
        f"{report['unfiltered_pagination_unique_count']}"
    )
    log(f"only_in_facet_union_count={report['only_in_facet_union_count']}")
    for url in report["only_in_facet_union"]:
        log(f"only_in_facet_union: {url}")

    log(
        "only_in_unfiltered_pagination_count="
        f"{report['only_in_unfiltered_pagination_count']}"
    )
    for url in report["only_in_unfiltered_pagination"]:
        log(f"only_in_unfiltered_pagination: {url}")

    log(f"sets_exactly_equal={report['sets_exactly_equal']}")


def retrieve_sioux_job_links(
    browser: Browser,
    *,
    job_limit: int | None = None,
) -> SiouxRetrievalResult:
    facet_union_urls, discipline_map = collect_job_links_via_facets(
        browser,
        job_limit=job_limit,
    )
    unfiltered_pagination_urls = collect_job_links_via_unfiltered_pagination(
        browser,
        job_limit=job_limit,
    )

    validation_report = build_collection_validation_report(
        facet_union_urls=facet_union_urls,
        unfiltered_pagination_urls=unfiltered_pagination_urls,
    )

    return SiouxRetrievalResult(
        job_links=facet_union_urls,
        discipline_map=discipline_map,
        validation_report=validation_report,
    )
