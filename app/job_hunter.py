#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
"""
Company jobs fetcher and ranker.

What it does:
- resolves the requested company source from the registry
- opens the company vacancies overview page
- collects vacancy detail links
- visits each vacancy page
- extracts useful fields
- ranks all extracted jobs against the selected candidate profile
- writes per-job ranking files under data/rankings
- optionally writes per-job raw and evaluated state files
- optionally writes the collection validation report under data/job_profiles/<company>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Sequence


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

from candidate_profile.llm.profile import CandidateProfileDocument
from infra.browser import launched_chromium
from infra.logging import log
from ranking.service import rank_jobs
from reporting import writer as report_writer
from sources.base import SourceDefinition
from sources.registry import get_source, list_available_sources

DEFAULT_CANDIDATE_PROFILE_DIR = Path("data/candidate_profiles")
DEFAULT_CANDIDATE_PROFILE_PATH = next(
    iter(sorted(DEFAULT_CANDIDATE_PROFILE_DIR.glob("*.json"))),
    DEFAULT_CANDIDATE_PROFILE_DIR / "Ibrahim_Saad_CV.json",
)


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
        type=Path,
        default=DEFAULT_CANDIDATE_PROFILE_PATH,
        help=(
            "Candidate profile JSON to rank against. "
            f"Defaults to {DEFAULT_CANDIDATE_PROFILE_PATH}."
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
        help="Write per-job evaluated job artifacts with embedded ranking metadata.",
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
) -> CandidateProfileDocument:
    profile_path = Path(candidate_profile_path)
    with profile_path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    if "candidate_id" not in payload:
        payload["candidate_id"] = profile_path.stem

    return CandidateProfileDocument.model_validate(payload)


def _build_evaluated_job_payload(
    job: Any,
    ranking_result: dict[str, Any],
) -> dict[str, Any]:
    payload = asdict(job)
    payload["ranking"] = ranking_result
    return payload


def fetch_source_jobs(
    browser: Any,
    source: SourceDefinition,
    *,
    candidate_profile: CandidateProfileDocument,
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

                jobs.append(job)
            except Exception as error:
                log(f"job failed: url='{url}' | error={error!r}")
    finally:
        detail_context.close()

    ranking_batch = rank_jobs(
        candidate_profile,
        jobs,
        log_message=log,
    )

    for job, ranking_result in zip(
        ranking_batch.ranked_jobs,
        ranking_batch.results,
    ):
        report_writer.write_ranking_result(
            ranking_result,
            log_message=log,
        )
        if write_evaluated_jobs:
            report_writer.write_evaluated_job(
                _build_evaluated_job_payload(job, ranking_result),
                company_slug=source.company_slug,
                log_message=log,
            )

    log(f"closing browser after fetching {len(jobs)} jobs")
    return FetchSourceJobsResult(
        jobs=jobs,
        ranking_results=ranking_batch.results,
        ranked_jobs=ranking_batch.ranked_jobs,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    try:
        source = get_source(args.company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    candidate_profile = load_candidate_profile(args.candidate_profile)
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
                write_raw_jobs=args.write_raw,
                write_evaluated_jobs=args.write_evaluated,
                write_validation_report=args.write_validation,
            )

    elapsed = time.time() - started_at
    log(
        f"done: total_jobs={len(result.jobs)} | "
        f"ranked_jobs={len(result.ranked_jobs)} | "
        f"elapsed_seconds={elapsed:.2f}"
    )


if __name__ == "__main__":
    main()
