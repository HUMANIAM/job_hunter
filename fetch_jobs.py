#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
"""
Company jobs fetcher.

What it does:
- resolves the requested company source from the registry
- opens the company vacancies overview page
- collects vacancy detail links
- visits each vacancy page
- extracts useful fields
- applies a keep/skip filter
- always writes the final kept-jobs file under data/analysis/<company>
- optionally writes raw, evaluated, and validation artifacts when requested

Requirements:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict
from typing import Any, Sequence

from playwright.sync_api import sync_playwright
from infra.browser import launched_chromium
from infra.logging import log
from ranking.service import evaluate_jobs
from reporting import writer as report_writer
from sources.base import SourceDefinition
from sources.registry import get_source, list_available_sources


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch jobs for a company source.")
    parser.add_argument(
        "--company",
        default="sioux",
        help=(
            "Company/source slug to fetch. "
            f"Available: {', '.join(list_available_sources())}"
        ),
    )
    parser.add_argument(
        "--write-raw",
        action="store_true",
        help="Write the raw collected jobs artifact.",
    )
    parser.add_argument(
        "--write-evaluated",
        action="store_true",
        help="Write the evaluated jobs artifact with keep/skip metadata.",
    )
    parser.add_argument(
        "--write-validation",
        action="store_true",
        help="Write the source validation artifact.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def fetch_source_jobs(
    browser: Any,
    source: SourceDefinition,
    *,
    write_validation_report: bool = False,
) -> list[Any]:
    retrieval = source.adapter.retrieve_job_links(browser)
    source.adapter.log_validation_report(retrieval.validation_report)
    if write_validation_report:
        report_writer.write_validation_report(
            retrieval.validation_report,
            company_slug=source.company_slug,
            log_message=log,
        )

    job_links = retrieval.job_links
    discipline_map = retrieval.discipline_map

    detail_context = browser.new_context()
    detail_page = detail_context.new_page()

    jobs: list[Any] = []
    for idx, url in enumerate(job_links, start=1):
        log(f"fetch progress: [{idx}/{len(job_links)}]")
        job = source.parser.fetch_job(
            detail_page,
            url,
            discipline_map.get(url, []),
            log_message=log,
        )
        if job:
            jobs.append(job)

    detail_context.close()
    log(f"closing browser after fetching {len(jobs)} jobs")
    return jobs


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        source = get_source(args.company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    started_at = time.time()
    log("program started")

    with sync_playwright() as p:
        log("launching chromium")
        with launched_chromium(p, headless=True) as browser:
            jobs = fetch_source_jobs(
                browser,
                source,
                write_validation_report=args.write_validation,
            )

    if args.write_raw:
        raw_jobs = [asdict(job) for job in jobs]
        report_writer.write_raw_jobs(
            jobs=raw_jobs,
            source=source.source_url,
            configured_countries=source.configured_countries,
            configured_languages=source.configured_languages,
            company_slug=source.company_slug,
            log_message=log,
        )

    log("starting evaluation")
    ranking_result = evaluate_jobs(jobs, log_message=log)

    if args.write_evaluated:
        report_writer.write_evaluated_jobs(
            jobs=ranking_result.evaluated_jobs,
            source=source.source_url,
            configured_countries=source.configured_countries,
            configured_languages=source.configured_languages,
            company_slug=source.company_slug,
            log_message=log,
        )

    report_writer.write_kept_jobs(
        jobs=[asdict(job) for job in ranking_result.kept_jobs],
        total_jobs=len(jobs),
        source=source.source_url,
        configured_countries=source.configured_countries,
        configured_languages=source.configured_languages,
        company_slug=source.company_slug,
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
