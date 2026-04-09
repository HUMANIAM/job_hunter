#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
"""
Company jobs fetcher and ranker.

What it does:
- resolves the requested company source from the registry
- reuses or builds the selected candidate profile once unless raw-only mode is used
- opens the company vacancies overview page
- collects vacancy detail links
- visits each vacancy page
- extracts useful fields
- optionally writes raw state files
- writes one evaluated job profile per vacancy under data/job_profiles/<company>/evaluated
- ranks all extracted jobs against the selected candidate profile
- writes per-job ranking files under data/job_profiles/<company>/rankings/{match,mismatch}
- optionally writes the collection validation report under data/job_profiles/<company>
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Sequence


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def bootstrap_project_root() -> None:
    root_str = str(PROJECT_ROOT)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)

    # Keep relative output paths anchored to the repository root.
    if Path.cwd() != PROJECT_ROOT:
        os.chdir(PROJECT_ROOT)


bootstrap_project_root()

from playwright.sync_api import sync_playwright

from app import job_hunter_core
from candidate_profile.profile import (
    CandidateProfileDocument,
    compute_source_text_hash,
    extract_profile,
)
from infra.browser import launched_chromium
from infra.format_conversion import convert_to_text
from infra.logging import log
from ranking.service import rank_job
from reporting import writer as report_writer
from sources.base import SourceDefinition
from sources.registry import get_source, list_available_sources

DEFAULT_CANDIDATE_PROFILE_DIR = job_hunter_core.DEFAULT_CANDIDATE_PROFILE_DIR
DEFAULT_CANDIDATE_PROFILE_PATH = job_hunter_core.DEFAULT_CANDIDATE_PROFILE_PATH
DEFAULT_MATCH_SCORE_THRESHOLD = job_hunter_core.DEFAULT_MATCH_SCORE_THRESHOLD


@dataclass
class FetchSourceJobsResult:
    jobs: list[Any]
    ranking_results: list[dict[str, Any]]
    ranked_jobs: list[Any]


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
        "--candidate-profile",
        "--cv",
        type=Path,
        dest="candidate_profile",
        default=DEFAULT_CANDIDATE_PROFILE_PATH,
        help=(
            "Candidate profile JSON/CV path to rank against. "
            f"Defaults to {DEFAULT_CANDIDATE_PROFILE_PATH}."
        ),
    )
    parser.add_argument(
        "--write-raw",
        action="store_true",
        help=(
            "Also write raw artifacts: structured JSON under "
            "data/job_profiles/<company>/raw_structured and page HTML under "
            "data/job_profiles/<company>/raw."
        ),
    )
    parser.add_argument(
        "--raw-only",
        action="store_true",
        help=(
            "Fetch and write only raw artifacts, skipping evaluated outputs and ranking."
        ),
    )
    parser.add_argument(
        "--write-evaluated",
        action="store_true",
        help="Deprecated compatibility flag; evaluated artifacts are written by default.",
    )
    parser.add_argument(
        "--write-validation",
        action="store_true",
        help="Write the source validation artifact.",
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of jobs to collect and rank.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def load_candidate_profile(
    candidate_profile_path: Path | str,
    *,
    log_message: Callable[[str], None] | None = None,
) -> CandidateProfileDocument:
    return job_hunter_core.load_candidate_profile(
        candidate_profile_path,
        default_candidate_profile_dir=DEFAULT_CANDIDATE_PROFILE_DIR,
        compute_source_text_hash_fn=compute_source_text_hash,
        extract_profile_fn=extract_profile,
        convert_to_text_fn=convert_to_text,
        write_candidate_profile_fn=report_writer.write_candidate_profile,
        log_message=log_message,
    )


def _capture_page_html(page: Any) -> str | None:
    try:
        return page.content()
    except Exception:
        return None


def fetch_source_jobs(
    browser: Any,
    source: SourceDefinition,
    *,
    candidate_profile: CandidateProfileDocument | None,
    job_limit: int | None = None,
    write_raw_jobs: bool = False,
    write_evaluated_jobs: bool = False,
    write_validation_report: bool = False,
    raw_only: bool = False,
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
    ranking_results: list[dict[str, Any]] = []
    ranked_jobs: list[Any] = []
    try:
        for idx, url in enumerate(job_links, start=1):
            log(f"fetch progress: [{idx}/{len(job_links)}]")
            try:
                parser_fetch = source.parser.fetch_job
                if raw_only:
                    parser_fetch = getattr(source.parser, "fetch_raw_job", parser_fetch)

                job = parser_fetch(
                    detail_page,
                    url,
                    discipline_map.get(url, []),
                    log_message=log,
                )
                if job is None:
                    continue

                raw_job_payload = asdict(job)
                jobs.append(job)

                if write_raw_jobs:
                    raw_html_content = _capture_page_html(detail_page)
                    report_writer.write_raw_job(
                        raw_job_payload,
                        company_slug=source.company_slug,
                        log_message=log,
                    )
                    if raw_html_content is not None:
                        report_writer.write_raw_html(
                            raw_html_content,
                            title=getattr(job, "title", None),
                            url=getattr(job, "url", None),
                            company_slug=source.company_slug,
                            log_message=log,
                        )
                if raw_only:
                    continue

                report_writer.write_evaluated_job(
                    raw_job_payload,
                    company_slug=source.company_slug,
                    log_message=log,
                )
                ranking_result = job_hunter_core.rank_and_write_job_artifacts(
                    candidate_profile=candidate_profile,
                    job=job,
                    job_payload=raw_job_payload,
                    company_slug=source.company_slug,
                    rank_job_fn=rank_job,
                    writer=report_writer,
                    match_score_threshold=DEFAULT_MATCH_SCORE_THRESHOLD,
                    index=len(ranking_results) + 1,
                    log_message=log,
                )
                if ranking_result["status"] != "match":
                    if ranking_result["decision_stage"] == "ranking":
                        log(
                            f"skip match: job_id='{job.job_id}' | "
                            f"score={ranking_result['score']:.3f} < "
                            f"{DEFAULT_MATCH_SCORE_THRESHOLD:.3f}"
                        )
                    else:
                        reason = (
                            ranking_result["rejection_reasons"][0]["reason"]
                            if ranking_result["rejection_reasons"]
                            else "unknown"
                        )
                        log(
                            f"skip match: job_id='{job.job_id}' | "
                            f"stage={ranking_result['decision_stage']} | "
                            f"reason={reason}"
                        )
                ranking_results.append(ranking_result)
                ranked_jobs.append(job)
            except Exception as error:
                log(f"job failed: url='{url}' | error={error!r}")
    finally:
        detail_context.close()

    log(f"closing browser after fetching {len(jobs)} jobs")
    return FetchSourceJobsResult(
        jobs=jobs,
        ranking_results=ranking_results,
        ranked_jobs=ranked_jobs,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        source = get_source(args.company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    raw_only = args.raw_only
    write_raw_jobs = args.write_raw or raw_only
    candidate_profile = None
    if not raw_only:
        candidate_profile = load_candidate_profile(
            args.candidate_profile,
            log_message=log,
        )
    started_at = time.time()
    log("program started")

    with sync_playwright() as p:
        log("launching chromium")
        with launched_chromium(p, headless=True) as browser:
            result = fetch_source_jobs(
                browser,
                source,
                candidate_profile=candidate_profile,
                job_limit=args.job_limit,
                write_raw_jobs=write_raw_jobs,
                write_evaluated_jobs=args.write_evaluated,
                write_validation_report=args.write_validation,
                raw_only=raw_only,
            )

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(result.jobs)} | "
        f"ranked_jobs={len(result.ranked_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
