#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
"""
Sioux jobs fetcher.

What it does:
- opens the Sioux vacancies overview page
- reads discipline facet URLs from the HTML
- visits each discipline in a fresh browser context to avoid sticky facet state
- follows real paging links when needed
- collects vacancy detail links under /vacancies/
- visits each vacancy page
- extracts useful fields
- applies a keep/skip filter
- writes four files:
    1) jobs_sioux_raw.json
    2) jobs_sioux_evaluated.json
    3) jobs_sioux.json
    4) jobs_sioux_validation.json

Requirements:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from playwright.sync_api import (
    Browser,
    Page,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)

START_URL = "https://vacancy.sioux.eu/"
BASE_URL = "https://vacancy.sioux.eu"

OUTPUT_DIR = Path("vacancies/sioux")
RAW_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_raw.json"
EVALUATED_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_evaluated.json"
OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux.json"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_validation.json"

# Reserved for future parsing-based filtering once structured fields are reliable.
TARGET_COUNTRIES: tuple[str, ...] = ()
TARGET_LANGUAGES: tuple[str, ...] = ()

JOB_URL_RE = re.compile(r"^https://vacancy\.sioux\.eu/vacancies/.+\.html$")

SKIP_TITLE_KEYWORDS = [
    "intern",
    "internship",
    "trainee",
    "graduate",
    "thesis",
    "recruiter",
    "talent acquisition",
    "hr",
    "human resources",
    "payroll",
    "compensation",
    "benefits",
    "people partner",
    "finance",
    "financial",
    "controller",
    "accounting",
    "tax",
    "treasury",
    "audit",
    "procurement",
    "purchasing",
    "buyer",
    "sourcing",
    "commodity manager",
    "supply chain",
    "logistics",
    "warehouse",
    "planner",
    "marketing",
    "brand",
    "communications",
    "communication",
    "public relations",
    "content specialist",
    "sales",
    "account manager",
    "business development",
    "commercial",
    "legal",
    "counsel",
    "compliance",
    "privacy officer",
    "facility",
    "facilities",
    "real estate",
    "workplace services",
    "customer support",
    "service desk",
    "helpdesk",
    "administrative",
    "administrator",
    "office manager",
    "operator",
    "technician",
    "assembler",
    "manufacturing associate",
]

KEEP_KEYWORDS = [
    "c++",
    "python",
    "software engineer",
    "software designer",
    "embedded",
    "firmware",
    "control",
    "controls",
    "machine control",
    "real-time",
    "rtos",
    "linux",
    "system software",
    "systems engineering",
    "mechatronics software",
    "automation",
    "robotics",
    "computer vision",
    "algorithm",
    "performance",
    "high-tech",
    "signal processing",
    "image processing",
    "ml",
    "machine learning",
    "inference",
]

LOW_SIGNAL_DESCRIPTION_KEYWORDS = {
    "control",
    "controls",
    "performance",
    "high-tech",
}


@dataclass
class Job:
    title: str
    url: str
    disciplines: list[str]
    location: str | None
    team: str | None
    work_experience: str | None
    educational_background: str | None
    workplace_type: str | None
    fulltime_parttime: str | None
    description_text: str


def log(message: str) -> None:
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {message}")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def absolutize_url(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/"):
        return BASE_URL + href
    return BASE_URL + "/" + href.lstrip("/")


def compile_keyword_patterns(keywords: Iterable[str]) -> tuple[re.Pattern[str], ...]:
    patterns: list[re.Pattern[str]] = []
    for keyword in keywords:
        escaped = re.escape(keyword.lower())
        patterns.append(re.compile(rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"))
    return tuple(patterns)


SKIP_TITLE_PATTERNS = compile_keyword_patterns(SKIP_TITLE_KEYWORDS)
KEEP_PATTERNS = compile_keyword_patterns(KEEP_KEYWORDS)


def matched_keywords(
    text: str,
    keywords: list[str],
    patterns: Iterable[re.Pattern[str]],
) -> list[str]:
    normalized_text = text.lower()
    return [
        keyword
        for keyword, pattern in zip(keywords, patterns)
        if pattern.search(normalized_text)
    ]


def wait_for_results(page: Page) -> None:
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(1200)
    try:
        page.locator("a.act-item-job-overview").first.wait_for(timeout=5000)
    except Exception:
        pass


def close_cookie_banner_if_present(page: Page) -> None:
    try:
        btn = page.locator("input.cookieClose.cookieAccept").first
        if btn.count() > 0 and btn.is_visible():
            btn.click(timeout=2000)
            page.wait_for_timeout(500)
            log("accepted cookie banner")
    except Exception:
        pass


def extract_discipline_facets(page: Page) -> list[tuple[str, str, int]]:
    facets: list[tuple[str, str, int]] = []

    links = page.locator("div.facets_item[data-type='functiegr'] a.filter-item-link")
    count = links.count()
    log(f"found {count} discipline facet links")

    for i in range(count):
        link = links.nth(i)
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


def collect_job_links_from_page(page: Page, context: str) -> set[str]:
    hrefs: set[str] = set()

    cards = page.locator("a.act-item-job-overview")
    count = cards.count()
    log(f"{context}: found {count} vacancy cards")

    for i in range(count):
        href = cards.nth(i).get_attribute("href")
        if not href:
            continue
        href = absolutize_url(href)
        if JOB_URL_RE.match(href):
            hrefs.add(href)

    log(f"{context}: collected {len(hrefs)} vacancy links from current page")
    return hrefs


def collect_links_from_paginated_listing(
    page: Page,
    context: str,
    expected_count: int | None = None,
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

        page_links = collect_job_links_from_page(page, f"{context} page {page_index}")
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

        next_url = get_next_page_url(page)
        if not next_url:
            log(f"{context}: no next page link")
            break

        if next_url in visited_pages:
            log(f"{context}: next page url already visited, stopping")
            break

        log(f"{context}: following next page -> {next_url}")
        page.goto(next_url, wait_until="domcontentloaded", timeout=30000)
        wait_for_results(page)
        page_index += 1

    return collected_links


def get_next_page_url(page: Page) -> str | None:
    """
    Read the actual Next link from paging controls.
    """
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


def collect_links_for_facet(browser: Browser, facet_name: str, facet_url: str, expected_count: int) -> set[str]:
    """
    Visit one facet in a fresh context so facet state does not leak across requests.
    Follow real paging links only when needed.
    """
    context = browser.new_context()
    page = context.new_page()

    try:
        log(f"facet '{facet_name}': opening fresh session")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_results(page)
        close_cookie_banner_if_present(page)

        log(f"facet '{facet_name}': opening facet url")
        page.goto(facet_url, wait_until="domcontentloaded", timeout=30000)
        wait_for_results(page)

        facet_links = collect_links_from_paginated_listing(
            page,
            context=f"facet '{facet_name}'",
            expected_count=expected_count,
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
) -> tuple[list[str], dict[str, list[str]]]:
    """
    Collect Sioux vacancy links by traversing each discipline facet in a fresh session.
    Also return a mapping:
        job_url -> sorted list of discipline names that reference that job
    """
    seed_context = browser.new_context()
    seed_page = seed_context.new_page()

    try:
        log(f"opening entry page: {START_URL}")
        seed_page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_results(seed_page)
        close_cookie_banner_if_present(seed_page)
        log(f"current page url: {seed_page.url}")

        facets = extract_discipline_facets(seed_page)
    finally:
        seed_context.close()

    all_hrefs: set[str] = set()
    url_to_disciplines: dict[str, set[str]] = {}

    for facet_name, facet_url, expected_count in facets:
        log(f"--- facet traversal: {facet_name} ---")
        facet_links = collect_links_for_facet(browser, facet_name, facet_url, expected_count)

        for url in facet_links:
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
    for idx, link in enumerate(job_links, start=1):
        log(
            f"link {idx}: {link} | disciplines={discipline_map.get(link, [])}"
        )

    return job_links, discipline_map


def collect_job_links_via_unfiltered_pagination(browser: Browser) -> list[str]:
    """
    Collect Sioux vacancy links from the main overview without using facets.
    """
    context = browser.new_context()
    page = context.new_page()

    try:
        log(f"unfiltered overview: opening entry page: {START_URL}")
        page.goto(START_URL, wait_until="domcontentloaded", timeout=30000)
        wait_for_results(page)
        close_cookie_banner_if_present(page)
        log(f"unfiltered overview: current page url: {page.url}")

        unfiltered_links = collect_links_from_paginated_listing(
            page,
            context="unfiltered overview",
        )
        job_links = sorted(unfiltered_links)

        log(
            "unfiltered overview: finished link collection: "
            f"{len(job_links)} total unique vacancy links"
        )
        for idx, link in enumerate(job_links, start=1):
            log(f"unfiltered overview link {idx}: {link}")

        return job_links
    finally:
        context.close()


def build_collection_validation_report(
    facet_union_urls: Iterable[str],
    unfiltered_pagination_urls: Iterable[str],
) -> dict:
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


def log_collection_validation_report(report: dict) -> None:
    log("collection validation report")
    log(f"facet_union_unique_count={report['facet_union_unique_count']}")
    log(
        "unfiltered_pagination_unique_count="
        f"{report['unfiltered_pagination_unique_count']}"
    )
    log(
        f"only_in_facet_union_count={report['only_in_facet_union_count']}"
    )
    for url in report["only_in_facet_union"]:
        log(f"only_in_facet_union: {url}")

    log(
        "only_in_unfiltered_pagination_count="
        f"{report['only_in_unfiltered_pagination_count']}"
    )
    for url in report["only_in_unfiltered_pagination"]:
        log(f"only_in_unfiltered_pagination: {url}")

    log(f"sets_exactly_equal={report['sets_exactly_equal']}")


def normalize_job_tag_key(value: str) -> str:
    return normalize_text(value).lower()


def extract_job_tags(page: Page) -> dict[str, str]:
    tags: dict[str, str] = {}

    try:
        tag_nodes = page.locator(".job-tags-wrapper .job-tag")
        tag_count = tag_nodes.count()
    except Exception:
        return tags

    for index in range(tag_count):
        tag_node = tag_nodes.nth(index)
        raw_key = (
            tag_node.get_attribute("data-type")
            or tag_node.get_attribute("title")
            or ""
        )
        key = normalize_job_tag_key(raw_key)
        if not key:
            continue

        try:
            value = normalize_text(
                tag_node.locator(".job-tag-value").first.inner_text(timeout=2000)
            )
        except Exception:
            continue

        if value:
            tags[key] = value

    return tags


def parse_job_posting_json_ld_blocks(
    json_ld_blocks: Iterable[str],
) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {
        "location": None,
        "country": None,
        "employment_type": None,
    }

    for json_ld_text in json_ld_blocks:
        try:
            payload = json.loads(json_ld_text)
        except json.JSONDecodeError:
            continue

        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if normalize_text(str(node.get("@type", ""))).lower() != "jobposting":
                continue

            job_location = node.get("jobLocation") or {}
            address = (
                job_location.get("address", {})
                if isinstance(job_location, dict)
                else {}
            )
            if isinstance(address, dict):
                locality = normalize_text(str(address.get("addressLocality", "")))
                country = normalize_text(str(address.get("addressCountry", "")))
                metadata["location"] = locality or None
                metadata["country"] = country or None

            employment_type = normalize_text(str(node.get("employmentType", "")))
            metadata["employment_type"] = employment_type or None
            return metadata

    return metadata


def extract_job_posting_metadata(page: Page) -> dict[str, str | None]:
    json_ld_blocks: list[str] = []

    try:
        script_nodes = page.locator("script[type='application/ld+json']")
        script_count = script_nodes.count()
    except Exception:
        return parse_job_posting_json_ld_blocks([])

    for index in range(script_count):
        try:
            script_text = script_nodes.nth(index).inner_text(timeout=2000)
        except Exception:
            continue
        if script_text:
            json_ld_blocks.append(script_text)

    return parse_job_posting_json_ld_blocks(json_ld_blocks)


def resolve_job_metadata(page: Page) -> dict[str, str | None]:
    job_tags = extract_job_tags(page)
    schema_metadata = extract_job_posting_metadata(page)

    return {
        "location": job_tags.get("location") or schema_metadata["location"],
        "country": schema_metadata["country"],
        "educational_background": job_tags.get("education level"),
        "fulltime_parttime": (
            job_tags.get("employment") or schema_metadata["employment_type"]
        ),
    }


def extract_value_by_label(page: Page, label: str) -> str | None:
    try:
        locator = page.locator(f"text='{label}'").first
        if locator.count() == 0:
            return None

        parent = locator.locator("xpath=..")
        block_text = normalize_text(parent.inner_text(timeout=2000))

        if block_text.lower().startswith(label.lower()):
            value = block_text[len(label):].strip(" :\n\t")
            return value or None

        return None
    except Exception:
        return None


def extract_description_text(page: Page) -> str:
    for selector in ["main", "article", "body"]:
        locator = page.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            text = normalize_text(locator.inner_text(timeout=3000))
            if len(text) > 200:
                return text
        except Exception:
            pass
    return ""


def fetch_job(page: Page, url: str, disciplines: list[str] | None = None) -> Job | None:
    log(f"opening vacancy page: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        log(f"warn: timeout opening {url}")
        return None

    try:
        title = page.locator("h1").first.inner_text(timeout=3000).strip()
    except Exception:
        log(f"warn: could not read title for {url}")
        return None

    metadata = resolve_job_metadata(page)
    description_text = extract_description_text(page)

    job = Job(
        title=normalize_text(title),
        url=url,
        disciplines=sorted(disciplines or []),
        location=metadata["location"],
        team=extract_value_by_label(page, "Team"),
        work_experience=extract_value_by_label(page, "Work experience"),
        educational_background=(
            metadata["educational_background"]
            or extract_value_by_label(page, "Educational background")
        ),
        workplace_type=extract_value_by_label(page, "Workplace type"),
        fulltime_parttime=(
            metadata["fulltime_parttime"]
            or extract_value_by_label(page, "Fulltime/parttime")
        ),
        description_text=description_text,
    )

    log(
        "extracted job: "
        f"title='{job.title}', "
        f"disciplines={job.disciplines}, "
        f"location='{job.location}', "
        f"country='{metadata['country']}', "
        f"employment='{job.fulltime_parttime}', "
        f"education='{job.educational_background}', "
        f"description_len={len(job.description_text)}"
    )
    return job


def evaluate_job(job: Job) -> dict:
    title = job.title or ""
    description = job.description_text or ""

    title_hits = matched_keywords(title, KEEP_KEYWORDS, KEEP_PATTERNS)
    if title_hits:
        return {
            "decision": "keep",
            "reason": "title_keep_match",
            "skip_hits": [],
            "title_hits": title_hits,
            "description_hits": [],
        }

    skip_hits = matched_keywords(title, SKIP_TITLE_KEYWORDS, SKIP_TITLE_PATTERNS)
    if skip_hits:
        return {
            "decision": "skip",
            "reason": "skip_title_keywords",
            "skip_hits": skip_hits,
            "title_hits": [],
            "description_hits": [],
        }

    description_hits_all = matched_keywords(description, KEEP_KEYWORDS, KEEP_PATTERNS)
    description_hits = [
        keyword
        for keyword in description_hits_all
        if keyword not in LOW_SIGNAL_DESCRIPTION_KEYWORDS
    ]

    if len(description_hits) >= 2:
        return {
            "decision": "keep",
            "reason": "description_keep_match",
            "skip_hits": [],
            "title_hits": [],
            "description_hits": description_hits,
        }

    return {
        "decision": "skip",
        "reason": "insufficient_keep_signal",
        "skip_hits": [],
        "title_hits": [],
        "description_hits": description_hits,
    }


def write_json(path: Path | str, payload: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    log(f"wrote file: {path}")


def main() -> None:
    started_at = time.time()
    log("program started")

    with sync_playwright() as p:
        log("launching chromium")
        browser = p.chromium.launch(headless=True)

        facet_union_urls, discipline_map = collect_job_links_via_facets(browser)
        unfiltered_pagination_urls = collect_job_links_via_unfiltered_pagination(browser)

        validation_report = build_collection_validation_report(
            facet_union_urls=facet_union_urls,
            unfiltered_pagination_urls=unfiltered_pagination_urls,
        )
        log_collection_validation_report(validation_report)
        write_json(VALIDATION_OUTPUT_PATH, validation_report)

        job_links = facet_union_urls

        detail_context = browser.new_context()
        detail_page = detail_context.new_page()

        jobs: list[Job] = []
        for idx, url in enumerate(job_links, start=1):
            log(f"fetch progress: [{idx}/{len(job_links)}]")
            job = fetch_job(detail_page, url, discipline_map.get(url, []))
            if job:
                jobs.append(job)

        detail_context.close()
        log(f"closing browser after fetching {len(jobs)} jobs")
        browser.close()

    raw_payload = {
        "fetched_at_unix": int(time.time()),
        "source": START_URL,
        "configured_countries": list(TARGET_COUNTRIES),
        "configured_languages": list(TARGET_LANGUAGES),
        "total_jobs": len(jobs),
        "jobs": [asdict(job) for job in jobs],
    }
    write_json(RAW_OUTPUT_PATH, raw_payload)

    log("starting evaluation")
    evaluated_jobs: list[dict] = []
    relevant_jobs: list[Job] = []

    for idx, job in enumerate(jobs, start=1):
        evaluation = evaluate_job(job)

        if evaluation["decision"] == "keep":
            log(
                f"KEEP [{idx}] '{job.title}' | "
                f"reason={evaluation['reason']} | "
                f"title_hits={evaluation['title_hits']} | "
                f"description_hits={evaluation['description_hits']}"
            )
            relevant_jobs.append(job)
        else:
            log(
                f"SKIP [{idx}] '{job.title}' | "
                f"reason={evaluation['reason']} | "
                f"skip_hits={evaluation['skip_hits']} | "
                f"description_hits={evaluation['description_hits']}"
            )

        job_dict = asdict(job)
        job_dict["decision"] = evaluation["decision"]
        job_dict["reason"] = evaluation["reason"]
        job_dict["skip_hits"] = evaluation["skip_hits"]
        job_dict["title_hits"] = evaluation["title_hits"]
        job_dict["description_hits"] = evaluation["description_hits"]
        evaluated_jobs.append(job_dict)

    evaluated_payload = {
        "fetched_at_unix": int(time.time()),
        "source": START_URL,
        "configured_countries": list(TARGET_COUNTRIES),
        "configured_languages": list(TARGET_LANGUAGES),
        "total_jobs": len(jobs),
        "jobs": evaluated_jobs,
    }
    write_json(EVALUATED_OUTPUT_PATH, evaluated_payload)

    kept_payload = {
        "fetched_at_unix": int(time.time()),
        "source": START_URL,
        "configured_countries": list(TARGET_COUNTRIES),
        "configured_languages": list(TARGET_LANGUAGES),
        "total_jobs": len(jobs),
        "relevant_jobs": len(relevant_jobs),
        "jobs": [asdict(job) for job in relevant_jobs],
    }
    write_json(OUTPUT_PATH, kept_payload)

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(jobs)} | "
        f"relevant_jobs={len(relevant_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
