#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
"""
Company jobs fetcher and ranker.

What it does:
- resolves the requested company source from the registry
- reuses or builds the selected candidate profile once
- opens the company vacancies overview page
- collects vacancy detail links
- visits each vacancy page
- extracts useful fields
- writes one evaluated job profile per vacancy under data/job_profiles/<company>/evaluated
- ranks all extracted jobs against the selected candidate profile
- writes per-job ranking files under data/rankings
- writes per-job match artifacts under data/job_profiles/<company>/match
- optionally writes raw state files
- optionally writes the collection validation report under data/job_profiles/<company>
"""

from __future__ import annotations

import argparse
import json
import os
import re
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

from candidate_profile.llm.profile import (
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

DEFAULT_CANDIDATE_PROFILE_DIR = Path("data/candidate_profiles")
DEFAULT_CANDIDATE_PROFILE_PATH = next(
    iter(sorted(DEFAULT_CANDIDATE_PROFILE_DIR.glob("*.json"))),
    DEFAULT_CANDIDATE_PROFILE_DIR / "Ibrahim_Saad_CV.json",
)
_CANDIDATE_PROFILE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


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
        help="Also write duplicate per-job raw artifacts under data/job_profiles/<company>/raw.",
    )
    parser.add_argument(
        "--write-evaluated",
        action="store_true",
        help="Deprecated compatibility flag; evaluated and match artifacts are written by default.",
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
    profile_path = Path(candidate_profile_path)
    if profile_path.suffix.lower() != ".json":
        return _extract_candidate_profile_from_source(
            profile_path,
            log_message=log_message,
        )

    with profile_path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    if "candidate_id" not in payload:
        payload["candidate_id"] = profile_path.stem

    return CandidateProfileDocument.model_validate(payload)


def _candidate_profile_stem(path: Path | str) -> str:
    source_path = Path(path)
    stem = _CANDIDATE_PROFILE_FILENAME_RE.sub("_", source_path.stem).strip("._")
    return stem or "candidate_profile"


def _candidate_profile_output_path_for(source_path: Path | str) -> Path:
    return DEFAULT_CANDIDATE_PROFILE_DIR / f"{_candidate_profile_stem(source_path)}.json"


def _extract_candidate_profile_from_source(
    source_path: Path | str,
    *,
    log_message: Callable[[str], None] | None = None,
) -> CandidateProfileDocument:
    resolved_source_path = Path(source_path)
    candidate_profile_path = _candidate_profile_output_path_for(resolved_source_path)
    profile_text = convert_to_text(resolved_source_path)
    source_text_hash = compute_source_text_hash(profile_text)

    if candidate_profile_path.exists():
        existing_profile = load_candidate_profile(candidate_profile_path)
        if existing_profile.source_text_hash == source_text_hash:
            if log_message is not None:
                log_message(f"reusing candidate profile: {candidate_profile_path}")
            return existing_profile

    candidate_profile = extract_profile(
        profile_text,
        candidate_id=_candidate_profile_stem(resolved_source_path),
    )
    report_writer.write_candidate_profile(
        candidate_profile.model_dump(mode="json"),
        output_path=candidate_profile_path,
        log_message=log_message,
    )
    return candidate_profile


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
    ranking_results: list[dict[str, Any]] = []
    ranked_jobs: list[Any] = []
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
                jobs.append(job)

                if write_raw_jobs:
                    report_writer.write_raw_job(
                        raw_job_payload,
                        company_slug=source.company_slug,
                        log_message=log,
                    )
                report_writer.write_evaluated_job(
                    raw_job_payload,
                    company_slug=source.company_slug,
                    log_message=log,
                )
                ranking_result = rank_job(
                    candidate_profile,
                    job,
                    index=len(ranking_results) + 1,
                    log_message=log,
                )
                report_writer.write_ranking_result(
                    ranking_result,
                    log_message=log,
                )
                report_writer.write_match_job(
                    _build_evaluated_job_payload(job, ranking_result),
                    company_slug=source.company_slug,
                    log_message=log,
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
