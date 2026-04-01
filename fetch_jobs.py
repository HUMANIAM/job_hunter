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
from typing import Iterable

from playwright.sync_api import (
    Page,
    sync_playwright,
)
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)
from reporting import writer as report_writer
from sources.sioux import adapter as sioux_adapter

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


def main() -> None:
    started_at = time.time()
    log("program started")

    with sync_playwright() as p:
        log("launching chromium")
        browser = p.chromium.launch(headless=True)

        retrieval = sioux_adapter.retrieve_sioux_job_links(browser)
        sioux_adapter.log_collection_validation_report(retrieval.validation_report)
        report_writer.write_validation_report(
            retrieval.validation_report,
            log_message=log,
        )

        job_links = retrieval.job_links
        discipline_map = retrieval.discipline_map

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

    raw_jobs = [asdict(job) for job in jobs]
    report_writer.write_raw_jobs(
        jobs=raw_jobs,
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

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

    report_writer.write_evaluated_jobs(
        jobs=evaluated_jobs,
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

    report_writer.write_kept_jobs(
        jobs=[asdict(job) for job in relevant_jobs],
        total_jobs=len(jobs),
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(jobs)} | "
        f"relevant_jobs={len(relevant_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
