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

import time
from dataclasses import asdict

from playwright.sync_api import sync_playwright
from infra.browser import launched_chromium
from infra.logging import log
from ranking.service import evaluate_jobs
from reporting import writer as report_writer
from sources.sioux import adapter as sioux_adapter
from sources.sioux import parser as sioux_parser


def main() -> None:
    started_at = time.time()
    log("program started")

    with sync_playwright() as p:
        log("launching chromium")
        with launched_chromium(p, headless=True) as browser:
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

    raw_jobs = [asdict(job) for job in jobs]
    report_writer.write_raw_jobs(
        jobs=raw_jobs,
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

    log("starting evaluation")
    ranking_result = evaluate_jobs(jobs, log_message=log)

    report_writer.write_evaluated_jobs(
        jobs=ranking_result.evaluated_jobs,
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

    report_writer.write_kept_jobs(
        jobs=[asdict(job) for job in ranking_result.kept_jobs],
        total_jobs=len(jobs),
        source=sioux_adapter.START_URL,
        configured_countries=sioux_adapter.TARGET_COUNTRIES,
        configured_languages=sioux_adapter.TARGET_LANGUAGES,
        log_message=log,
    )

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(jobs)} | "
        f"relevant_jobs={len(ranking_result.kept_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
