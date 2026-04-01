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

import re
import time
from dataclasses import asdict
from typing import Iterable

from playwright.sync_api import sync_playwright
from reporting import writer as report_writer
from sources.sioux import adapter as sioux_adapter
from sources.sioux import parser as sioux_parser

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


def log(message: str) -> None:
    now = time.strftime("%H:%M:%S")
    print(f"[{now}] {message}")


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


def evaluate_job(job: sioux_parser.SiouxJob) -> dict:
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

        jobs: list[sioux_parser.SiouxJob] = []
        for idx, url in enumerate(job_links, start=1):
            log(f"fetch progress: [{idx}/{len(job_links)}]")
            job = sioux_parser.fetch_job(
                detail_page,
                url,
                discipline_map.get(url, []),
                log_message=log,
            )
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
    relevant_jobs: list[sioux_parser.SiouxJob] = []

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
