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
from clients.job_profiling.profiling import (
    profile_vacancy_text,
)
from infra import json_io
from infra.logging import log
from shared.cli import positive_int_arg

DEFAULT_HTML_INPUT_DIR = Path("data/refactor/jobs/sioux/html")
DEFAULT_PREPROCESSING_OUTPUT_DIR = Path("data/refactor/jobs/sioux/preprocessing")
DEFAULT_VACANCY_PROFILE_OUTPUT_DIR = Path("data/refactor/jobs/sioux/vacancy_profiles")
_KNOWN_PIPELINE_STAGES = {"pre", "ext"}


@dataclass
class JobProfilingResult:
    input_path: Path
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
    parser = argparse.ArgumentParser(
        description=(
            "Run the job profiling pipeline for raw HTML or preprocessed "
            "vacancy text. Existing stage outputs are skipped automatically."
        )
    )
    parser.add_argument(
        "input_path",
        type=Path,
        nargs="?",
        help=(
            "Input file or directory matching the selected pipeline: .html for "
            "`pre` or `pre,ext`; .txt for `ext`."
        ),
    )
    parser.add_argument(
        "--pre-output-dir",
        type=Path,
        default=DEFAULT_PREPROCESSING_OUTPUT_DIR,
        help=(
            "Directory for preprocessed vacancy text output. "
            "Defaults to data/refactor/jobs/sioux/preprocessing."
        ),
    )
    parser.add_argument(
        "--ext-output-dir",
        type=Path,
        default=DEFAULT_VACANCY_PROFILE_OUTPUT_DIR,
        help=(
            "Directory for vacancy profile JSON output. "
            "Defaults to data/refactor/jobs/sioux/vacancy_profiles."
        ),
    )
    parser.add_argument(
        "--pipeline",
        required=True,
        help="Comma-separated pipeline stages. Available: pre, ext.",
    )
    parser.add_argument(
        "-n",
        type=positive_int_arg("-n"),
        help=(
            "Maximum number of pending jobs to process from a file or directory input."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    args.pipeline = _parse_pipeline(args.pipeline)
    if args.input_path is None:
        args.input_path = (
            DEFAULT_HTML_INPUT_DIR
            if "pre" in args.pipeline
            else args.pre_output_dir
        )
    return args


def _resolve_html_path(html_path: Path) -> Path:
    if not html_path.exists():
        raise SystemExit(f"html path does not exist: {html_path}")
    if not html_path.is_file():
        raise SystemExit(f"html path must be a file: {html_path}")
    if html_path.suffix.lower() != ".html":
        raise SystemExit(f"html path must point to a .html file: {html_path}")
    return html_path


def _resolve_cleaned_text_path(cleaned_text_path: Path) -> Path:
    if not cleaned_text_path.exists():
        raise SystemExit(f"preprocessed text path does not exist: {cleaned_text_path}")
    if not cleaned_text_path.is_file():
        raise SystemExit(f"preprocessed text path must be a file: {cleaned_text_path}")
    if cleaned_text_path.suffix.lower() != ".txt":
        raise SystemExit(f"preprocessed text path must point to a .txt file: {cleaned_text_path}")
    return cleaned_text_path


def _resolve_directory_inputs(
    directory_path: Path,
    *,
    extensions: tuple[str, ...],
    limit: int | None = None,
    empty_error_message: str,
) -> list[Path]:
    candidate_paths = sorted(
        path
        for path in directory_path.iterdir()
        if path.is_file() and path.suffix.lower() in extensions
    )
    if not candidate_paths:
        raise SystemExit(empty_error_message)
    if limit is not None:
        return candidate_paths[:limit]
    return candidate_paths


def _resolve_input_paths(
    input_path: Path,
    *,
    pipeline: Sequence[str],
    input_limit: int | None = None,
) -> list[Path]:
    if not input_path.exists():
        raise SystemExit(f"input path does not exist: {input_path}")

    if input_path.is_file():
        if "pre" in pipeline:
            return [_resolve_html_path(input_path)]

        if input_path.suffix.lower() == ".txt":
            return [_resolve_cleaned_text_path(input_path)]
        raise SystemExit(
            "ext input path must point to a .txt file: "
            f"{input_path}"
        )

    if not input_path.is_dir():
        raise SystemExit(f"input path must be a file or directory: {input_path}")

    if "pre" in pipeline:
        return _resolve_directory_inputs(
            input_path,
            extensions=(".html",),
            limit=input_limit,
            empty_error_message=(
                f"html directory contains no .html files: {input_path}"
            ),
        )

    return _resolve_directory_inputs(
        input_path,
        extensions=(".txt",),
        limit=input_limit,
        empty_error_message=(
            "ext input directory contains no .txt files: "
            f"{input_path}"
        ),
    )


def _preprocessing_output_path_for(
    html_path: Path,
    preprocessing_output_dir: Path,
) -> Path:
    return preprocessing_output_dir / f"{html_path.stem}.txt"


def _vacancy_profile_output_path_for(
    html_path: Path,
    vacancy_profile_output_dir: Path,
) -> Path:
    return vacancy_profile_output_dir / f"{html_path.stem}.json"


def _final_output_path_for(
    input_path: Path,
    *,
    pipeline: Sequence[str],
    preprocessing_output_dir: Path,
    vacancy_profile_output_dir: Path,
) -> Path:
    if list(pipeline)[-1] == "pre":
        return _preprocessing_output_path_for(
            input_path,
            preprocessing_output_dir,
        )
    return _vacancy_profile_output_path_for(
        input_path,
        vacancy_profile_output_dir,
    )


def _pending_input_paths(
    input_paths: Sequence[Path],
    *,
    pipeline: Sequence[str],
    preprocessing_output_dir: Path,
    vacancy_profile_output_dir: Path,
    input_limit: int | None = None,
) -> list[Path]:
    pending_paths = [
        input_path
        for input_path in input_paths
        if not _final_output_path_for(
            input_path,
            pipeline=pipeline,
            preprocessing_output_dir=preprocessing_output_dir,
            vacancy_profile_output_dir=vacancy_profile_output_dir,
        ).exists()
    ]
    if input_limit is not None:
        return pending_paths[:input_limit]
    return pending_paths


def _load_cleaned_vacancy_text(
    html_path: Path,
    preprocessing_output_dir: Path,
) -> str:
    cleaned_text_path = _preprocessing_output_path_for(
        html_path,
        preprocessing_output_dir,
    )
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


def _load_cleaned_vacancy_text_from_file(cleaned_text_path: Path) -> str:
    resolved_cleaned_text_path = _resolve_cleaned_text_path(cleaned_text_path)
    return resolved_cleaned_text_path.read_text(encoding="utf-8")


def run_job_profiling(
    *,
    html_path: Path,
    pipeline: Sequence[str],
    preprocessing_output_dir: Path = DEFAULT_PREPROCESSING_OUTPUT_DIR,
    vacancy_profile_output_dir: Path = DEFAULT_VACANCY_PROFILE_OUTPUT_DIR,
) -> JobProfilingResult:
    resolved_html_path = _resolve_html_path(html_path)
    normalized_pipeline = list(pipeline)
    raw_job_html = resolved_html_path.read_text(encoding="utf-8")
    phase_output_paths: dict[str, Path] = {}
    cleaned_text: str | None = None

    if "pre" in normalized_pipeline:
        cleaned_text = preprocess_job_html(raw_job_html)
        output_path = _preprocessing_output_path_for(
            resolved_html_path,
            preprocessing_output_dir,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(cleaned_text, encoding="utf-8")
        phase_output_paths["pre"] = output_path
        log(f"wrote file: {output_path}")

    if "ext" in normalized_pipeline:
        if cleaned_text is None:
            cleaned_text = _load_cleaned_vacancy_text(
                resolved_html_path,
                preprocessing_output_dir,
            )
        vacancy_profile = profile_vacancy_text(cleaned_text)
        output_path = _vacancy_profile_output_path_for(
            resolved_html_path,
            vacancy_profile_output_dir,
        )
        json_io.write_json(
            output_path,
            vacancy_profile.model_dump(mode="json"),
        )
        phase_output_paths["ext"] = output_path
        log(f"wrote file: {output_path}")

    return JobProfilingResult(
        input_path=resolved_html_path,
        phase_output_paths=phase_output_paths,
    )


def run_vacancy_profile_extraction(
    *,
    cleaned_text_path: Path,
    vacancy_profile_output_dir: Path = DEFAULT_VACANCY_PROFILE_OUTPUT_DIR,
) -> JobProfilingResult:
    resolved_cleaned_text_path = _resolve_cleaned_text_path(cleaned_text_path)
    cleaned_text = _load_cleaned_vacancy_text_from_file(resolved_cleaned_text_path)
    vacancy_profile = profile_vacancy_text(cleaned_text)
    output_path = _vacancy_profile_output_path_for(
        resolved_cleaned_text_path,
        vacancy_profile_output_dir,
    )
    json_io.write_json(
        output_path,
        vacancy_profile.model_dump(mode="json"),
    )
    log(f"wrote file: {output_path}")
    return JobProfilingResult(
        input_path=resolved_cleaned_text_path,
        phase_output_paths={"ext": output_path},
    )


def run_job_profiling_for_input_path(
    *,
    input_path: Path,
    pipeline: Sequence[str],
    input_limit: int | None = None,
    preprocessing_output_dir: Path = DEFAULT_PREPROCESSING_OUTPUT_DIR,
    vacancy_profile_output_dir: Path = DEFAULT_VACANCY_PROFILE_OUTPUT_DIR,
) -> list[JobProfilingResult]:
    resolved_input_paths = _resolve_input_paths(
        input_path,
        pipeline=pipeline,
        input_limit=None,
    )
    pending_input_paths = _pending_input_paths(
        resolved_input_paths,
        pipeline=pipeline,
        preprocessing_output_dir=preprocessing_output_dir,
        vacancy_profile_output_dir=vacancy_profile_output_dir,
        input_limit=input_limit,
    )
    results: list[JobProfilingResult] = []
    for resolved_input_path in pending_input_paths:
        if resolved_input_path.suffix.lower() == ".txt":
            results.append(
                run_vacancy_profile_extraction(
                    cleaned_text_path=resolved_input_path,
                    vacancy_profile_output_dir=vacancy_profile_output_dir,
                )
            )
            continue

        results.append(
            run_job_profiling(
                html_path=resolved_input_path,
                pipeline=pipeline,
                preprocessing_output_dir=preprocessing_output_dir,
                vacancy_profile_output_dir=vacancy_profile_output_dir,
            )
        )
    return results


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log(
        f"job profiling started: input={args.input_path} | "
        f"pipeline={','.join(args.pipeline)}"
    )
    results = run_job_profiling_for_input_path(
        input_path=args.input_path,
        pipeline=args.pipeline,
        input_limit=args.n,
        preprocessing_output_dir=args.pre_output_dir,
        vacancy_profile_output_dir=args.ext_output_dir,
    )
    log(
        f"job profiling done: input={args.input_path} | "
        f"files={len(results)}"
    )


if __name__ == "__main__":
    main()
