#!/usr/bin/env python3
"""
Rerank existing job profile JSON artifacts against candidate profile JSON artifacts.

What it does:
- loads one or more candidate profile JSON files
- loads one or more job profile JSON files
- reruns ranking without fetching or parsing new vacancies
- rewrites ranking outputs under data/job_profiles/<company>/rankings/{match,mismatch}
- removes stale legacy job decision artifacts and stale opposite ranking artifacts
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    raise SystemExit("Run this CLI as a module: python -m app.rerank_jobs ...")

from app_job_hunter_ref import job_hunter_core
from infra.logging import log
from ranking.service import rank_job
from reporting import writer as report_writer

DEFAULT_JOB_PROFILE_DIR = Path("data/job_profiles/sioux/evaluated")
DEFAULT_CANDIDATE_PROFILE_DIR = job_hunter_core.DEFAULT_CANDIDATE_PROFILE_DIR
DEFAULT_COMPANY_SLUG = job_hunter_core.DEFAULT_COMPANY_SLUG
DEFAULT_MATCH_SCORE_THRESHOLD = job_hunter_core.DEFAULT_MATCH_SCORE_THRESHOLD


@dataclass
class RerankJobsResult:
    candidate_profile_paths: list[Path]
    job_profile_paths: list[Path]
    ranking_results: list[dict[str, Any]]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Rerank existing job profile JSON files.")
    parser.add_argument(
        "--job-profile",
        type=Path,
        help=(
            "Job profile JSON file or directory. Defaults to "
            f"{DEFAULT_JOB_PROFILE_DIR}."
        ),
    )
    parser.add_argument(
        "--candidate-profile",
        "--cv",
        dest="candidate_profile",
        type=Path,
        help=(
            "Candidate profile JSON file or directory. Defaults to "
            f"{DEFAULT_CANDIDATE_PROFILE_DIR}/*.json."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def _resolve_json_paths(
    path: Path | None,
    *,
    default_dir: Path,
    label: str,
) -> list[Path]:
    if path is None:
        resolved_paths = sorted(default_dir.glob("*.json"))
    elif path.is_dir():
        resolved_paths = sorted(path.glob("*.json"))
    else:
        resolved_paths = [path]

    if not resolved_paths:
        raise SystemExit(f"no {label} JSON files found")

    for resolved_path in resolved_paths:
        if resolved_path.suffix.lower() != ".json":
            raise SystemExit(f"{label} must be a JSON file or directory: {resolved_path}")
        if not resolved_path.exists():
            raise SystemExit(f"{label} does not exist: {resolved_path}")

    return resolved_paths


def rerank_job_profiles(
    *,
    candidate_profile_paths: Sequence[Path],
    job_profile_paths: Sequence[Path],
    log_message=None,
) -> RerankJobsResult:
    ranking_results: list[dict[str, Any]] = []

    for candidate_profile_path in candidate_profile_paths:
        candidate_profile = job_hunter_core.load_candidate_profile(
            candidate_profile_path,
            log_message=log_message,
        )

        for job_profile_path in job_profile_paths:
            job_payload = job_hunter_core.load_job_profile_payload(job_profile_path)
            job = job_hunter_core.payload_to_namespace(job_payload)
            company_slug = job_hunter_core.infer_company_slug(job_profile_path)
            ranking_result = job_hunter_core.rank_and_write_job_artifacts(
                candidate_profile=candidate_profile,
                job=job,
                job_payload=job_payload,
                company_slug=company_slug,
                rank_job_fn=rank_job,
                writer=report_writer,
                match_score_threshold=DEFAULT_MATCH_SCORE_THRESHOLD,
                log_message=log_message,
            )
            ranking_results.append(ranking_result)

    return RerankJobsResult(
        candidate_profile_paths=list(candidate_profile_paths),
        job_profile_paths=list(job_profile_paths),
        ranking_results=ranking_results,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    candidate_profile_paths = _resolve_json_paths(
        args.candidate_profile,
        default_dir=DEFAULT_CANDIDATE_PROFILE_DIR,
        label="candidate profile",
    )
    job_profile_paths = _resolve_json_paths(
        args.job_profile,
        default_dir=DEFAULT_JOB_PROFILE_DIR,
        label="job profile",
    )

    log(
        f"rerank started: candidates={len(candidate_profile_paths)} | "
        f"jobs={len(job_profile_paths)}"
    )
    result = rerank_job_profiles(
        candidate_profile_paths=candidate_profile_paths,
        job_profile_paths=job_profile_paths,
        log_message=log,
    )
    log(
        f"rerank done: candidates={len(result.candidate_profile_paths)} | "
        f"jobs={len(result.job_profile_paths)} | "
        f"rankings={len(result.ranking_results)}"
    )


if __name__ == "__main__":
    main()
