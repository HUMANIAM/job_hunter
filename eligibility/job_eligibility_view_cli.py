#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this CLI as a module: python -m eligibility.job_eligibility_view_cli ..."
    )

from app_job_hunter_ref import job_hunter_core
from eligibility.job_eligibility_view import (
    extract_job_eligibility_view,
    get_default_job_eligibility_view_extractor,
)
from infra import json_io
from infra.logging import log


DEFAULT_JOB_PROFILE_DIR = Path("data/job_profiles/sioux/raw_structured")
DEFAULT_OUTPUT_DIR = Path("data/job_profiles/sioux/eligibility")


@dataclass
class BuildJobEligibilityViewsResult:
    job_profile_paths: list[Path]
    output_paths: list[Path]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build job eligibility JSON files from job profile JSON files."
    )
    parser.add_argument(
        "--job-profile",
        type=Path,
        help=(
            "Job profile JSON file or directory. Defaults to "
            f"{DEFAULT_JOB_PROFILE_DIR}."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Eligibility output directory. Defaults to {DEFAULT_OUTPUT_DIR}.",
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


def build_job_eligibility_views(
    *,
    job_profile_paths: Sequence[Path],
    output_dir: Path,
    extractor: Any | None = None,
    load_job_profile_payload_fn=job_hunter_core.load_job_profile_payload,
    extract_job_eligibility_view_fn=extract_job_eligibility_view,
    write_json_fn=json_io.write_json,
    log_message=None,
) -> BuildJobEligibilityViewsResult:
    active_extractor = extractor or get_default_job_eligibility_view_extractor()
    output_paths: list[Path] = []

    for job_profile_path in job_profile_paths:
        job_payload = load_job_profile_payload_fn(job_profile_path)
        eligibility_view = extract_job_eligibility_view_fn(
            job_payload,
            extractor=active_extractor,
        )
        output_path = output_dir / job_profile_path.name
        write_json_fn(
            output_path,
            eligibility_view.model_dump(mode="json", exclude_none=True),
        )
        if log_message is not None:
            log_message(f"wrote file: {output_path}")
        output_paths.append(output_path)

    return BuildJobEligibilityViewsResult(
        job_profile_paths=list(job_profile_paths),
        output_paths=output_paths,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    job_profile_paths = _resolve_json_paths(
        args.job_profile,
        default_dir=DEFAULT_JOB_PROFILE_DIR,
        label="job profile",
    )

    if args.output_dir.exists() and not args.output_dir.is_dir():
        raise SystemExit(f"output dir must be a directory path: {args.output_dir}")

    log(f"eligibility build started: jobs={len(job_profile_paths)}")
    result = build_job_eligibility_views(
        job_profile_paths=job_profile_paths,
        output_dir=args.output_dir,
        log_message=log,
    )
    log(
        f"eligibility build done: jobs={len(result.job_profile_paths)} | "
        f"outputs={len(result.output_paths)}"
    )


if __name__ == "__main__":
    main()
