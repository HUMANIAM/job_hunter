#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this CLI as a module: python -m clients.job_profiling.job_profiling_cli ..."
    )

from clients.job_profiling.preprocessing.job_profiling_preporcessor import (
    preprocess_job_html,
)
from clients.job_profiling.vacancy_profiler.vacancy_profiler import (
    profile_vacancy_text,
)
from infra import json_io
from infra.logging import log

DEFAULT_PREPROCESSING_OUTPUT_DIR = Path("data/refactor/jobs/sioux/preprocessing")
DEFAULT_VACANCY_PROFILE_OUTPUT_DIR = Path("data/refactor/jobs/sioux/vacancy_profiles")
DEFAULT_PIPELINE = ("pre",)
_KNOWN_PIPELINE_STAGES = {"pre", "ext"}


@dataclass
class JobProfilingResult:
    html_path: Path
    phase_output_paths: dict[str, Path]


def _parse_pipeline(value: str) -> list[str]:
    stages = [stage.strip().lower() for stage in value.split(",") if stage.strip()]
    if not stages:
        raise argparse.ArgumentTypeError("--pipeline must include at least one stage")

    deduped_stages = list(dict.fromkeys(stages))
    invalid_stages = [stage for stage in deduped_stages if stage not in _KNOWN_PIPELINE_STAGES]
    if invalid_stages:
        raise argparse.ArgumentTypeError(
            "unknown pipeline stage(s): "
            f"{', '.join(invalid_stages)}; expected one of: pre, ext"
        )

    return deduped_stages


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the job profiling pipeline for one HTML file.")
    parser.add_argument(
        "html_path",
        type=Path,
        help="Raw job HTML file path.",
    )
    parser.add_argument(
        "--pipeline",
        default="pre",
        help="Comma-separated pipeline stages. Available: pre, ext. Defaults to pre.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    args.pipeline = _parse_pipeline(args.pipeline)
    return args


def _resolve_html_path(html_path: Path) -> Path:
    if not html_path.exists():
        raise SystemExit(f"html path does not exist: {html_path}")
    if not html_path.is_file():
        raise SystemExit(f"html path must be a file: {html_path}")
    if html_path.suffix.lower() != ".html":
        raise SystemExit(f"html path must point to a .html file: {html_path}")
    return html_path


def _preprocessing_output_path_for(html_path: Path) -> Path:
    return DEFAULT_PREPROCESSING_OUTPUT_DIR / f"{html_path.stem}.txt"


def _vacancy_profile_output_path_for(html_path: Path) -> Path:
    return DEFAULT_VACANCY_PROFILE_OUTPUT_DIR / f"{html_path.stem}.json"


def _load_cleaned_vacancy_text(html_path: Path) -> str:
    cleaned_text_path = _preprocessing_output_path_for(html_path)
    if not cleaned_text_path.exists():
        raise SystemExit(
            "preprocessed vacancy text does not exist: "
            f"{cleaned_text_path}; run with --pipeline pre,ext or pre first"
        )
    if not cleaned_text_path.is_file():
        raise SystemExit(
            f"preprocessed vacancy text path must be a file: {cleaned_text_path}"
        )
    return cleaned_text_path.read_text(encoding="utf-8")


def run_job_profiling(
    *,
    html_path: Path,
    pipeline: Sequence[str],
) -> JobProfilingResult:
    resolved_html_path = _resolve_html_path(html_path)
    normalized_pipeline = list(pipeline)
    raw_job_html = resolved_html_path.read_text(encoding="utf-8")
    phase_output_paths: dict[str, Path] = {}
    cleaned_text: str | None = None

    if "pre" in normalized_pipeline:
        cleaned_text = preprocess_job_html(raw_job_html)
        output_path = _preprocessing_output_path_for(resolved_html_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_text, encoding="utf-8")
        phase_output_paths["pre"] = output_path
        log(f"wrote file: {output_path}")

    if "ext" in normalized_pipeline:
        if cleaned_text is None:
            cleaned_text = _load_cleaned_vacancy_text(resolved_html_path)
        vacancy_profile = profile_vacancy_text(cleaned_text)
        output_path = _vacancy_profile_output_path_for(resolved_html_path)
        json_io.write_json(
            output_path,
            vacancy_profile.model_dump(mode="json"),
        )
        phase_output_paths["ext"] = output_path
        log(f"wrote file: {output_path}")

    return JobProfilingResult(
        html_path=resolved_html_path,
        phase_output_paths=phase_output_paths,
    )


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log(
        f"job profiling started: html={args.html_path} | "
        f"pipeline={','.join(args.pipeline)}"
    )
    result = run_job_profiling(
        html_path=args.html_path,
        pipeline=args.pipeline,
    )
    log(
        f"job profiling done: html={result.html_path} | "
        f"outputs={len(result.phase_output_paths)}"
    )


if __name__ == "__main__":
    main()
