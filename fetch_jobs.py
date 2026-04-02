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
- writes final per-job match files under data/job_profiles/<company>/match
- optionally writes per-job raw and evaluated state files
- optionally writes the collection validation report under data/job_profiles/<company>

Requirements:
    pip install playwright
    playwright install chromium
"""

from __future__ import annotations

import argparse
import time
from dataclasses import asdict, dataclass
from typing import Any, Sequence

from playwright.sync_api import sync_playwright

from infra.browser import launched_chromium
from infra.logging import log
from ranking.evaluator import evaluate_job
from reporting import writer as report_writer
from sources.base import SourceDefinition
from sources.registry import get_source, list_available_sources


@dataclass
class FetchSourceJobsResult:
    jobs: list[Any]
    matched_jobs: list[Any]


def _positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("--job-limit must be >= 1")
    return parsed_value


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
        help="Write per-job raw collected job artifacts.",
    )
    parser.add_argument(
        "--write-evaluated",
        action="store_true",
        help="Write per-job evaluated job artifacts with keep/skip metadata.",
    )
    parser.add_argument(
        "--write-validation",
        action="store_true",
        help="Write the source validation artifact.",
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of jobs to collect and validate.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _log_evaluation(
    job: Any,
    evaluation: dict[str, Any],
    *,
    index: int,
    log_message,
) -> None:
    if log_message is None:
        return

    if evaluation["decision"] == "keep":
        log_message(
            f"KEEP [{index}] '{job.title}' | "
            f"reason={evaluation['reason']} | "
            f"title_hits={evaluation['title_hits']} | "
            f"description_hits={evaluation['description_hits']}"
        )
        return

    log_message(
        f"SKIP [{index}] '{job.title}' | "
        f"reason={evaluation['reason']} | "
        f"skip_hits={evaluation['skip_hits']} | "
        f"description_hits={evaluation['description_hits']}"
    )


def _evaluate_job_payload(
    job: Any,
    *,
    index: int,
    log_message,
) -> tuple[dict[str, Any], bool]:
    evaluation = evaluate_job(job)
    _log_evaluation(
        job,
        evaluation,
        index=index,
        log_message=log_message,
    )

    job_payload = asdict(job)
    job_payload["decision"] = evaluation["decision"]
    job_payload["reason"] = evaluation["reason"]
    job_payload["skip_hits"] = evaluation["skip_hits"]
    job_payload["title_hits"] = evaluation["title_hits"]
    job_payload["description_hits"] = evaluation["description_hits"]
    return job_payload, evaluation["decision"] == "keep"


def fetch_source_jobs(
    browser: Any,
    source: SourceDefinition,
    *,
    job_limit: int | None = None,
    write_raw_jobs: bool = False,
    write_evaluated_jobs: bool = False,
    write_validation_report: bool = False,
) -> FetchSourceJobsResult:
    retrieval = source.adapter.retrieve_job_links(
        browser,
        job_limit=job_limit,
    )
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
    matched_jobs: list[Any] = []
    try:
        for idx, url in enumerate(job_links, start=1):
            log(f"fetch progress: [{idx}/{len(job_links)}]")
            try:
                job = source.parser.fetch_job(
                    detail_page,
                    url,
                    discipline_map.get(url, []),
                    log_message=log,
                )
                if job is None:
                    continue

                raw_job_payload = asdict(job)
                if write_raw_jobs:
                    report_writer.write_raw_job(
                        raw_job_payload,
                        company_slug=source.company_slug,
                        log_message=log,
                    )

                evaluated_job_payload, is_match = _evaluate_job_payload(
                    job,
                    index=idx,
                    log_message=log,
                )
                if write_evaluated_jobs:
                    report_writer.write_evaluated_job(
                        evaluated_job_payload,
                        company_slug=source.company_slug,
                        log_message=log,
                    )

                if is_match:
                    report_writer.write_match_job(
                        raw_job_payload,
                        company_slug=source.company_slug,
                        log_message=log,
                    )
                    matched_jobs.append(job)

                jobs.append(job)
            except Exception as error:
                log(f"job failed: url='{url}' | error={error!r}")
    finally:
        detail_context.close()

    log(f"closing browser after fetching {len(jobs)} jobs")
    return FetchSourceJobsResult(
        jobs=jobs,
        matched_jobs=matched_jobs,
    )


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
            result = fetch_source_jobs(
                browser,
                source,
                job_limit=args.job_limit,
                write_raw_jobs=args.write_raw,
                write_evaluated_jobs=args.write_evaluated,
                write_validation_report=args.write_validation,
            )

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(result.jobs)} | "
        f"relevant_jobs={len(result.matched_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
