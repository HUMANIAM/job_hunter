#!/usr/bin/env python3
from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this CLI as a module: python -m clients.candidate_profiling.candidate_profiling_cli ..."
    )

from clients.candidate_profiling.candidate_profiling import profile_candidate_text
from infra import json_io
from infra.format_conversion import convert_to_text
from infra.logging import log
from shared.cli import positive_int_arg

DEFAULT_CANDIDATE_INPUT_PATH = Path("data/refactor/candidates/cvs")
DEFAULT_CANDIDATE_PROFILE_OUTPUT_PATH = Path("data/refactor/candidates/profiles")
_SUPPORTED_CANDIDATE_INPUT_SUFFIXES = (".docx", ".md", ".pdf", ".txt")


@dataclass
class CandidateProfilingResult:
    input_path: Path
    output_path: Path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run candidate profiling for a CV/resume file or a directory of CVs. "
            "Supported input formats: .docx, .md, .pdf, .txt."
        )
    )
    parser.add_argument(
        "input_path",
        type=Path,
        nargs="?",
        help=(
            "Candidate CV/resume input file or directory. "
            "Defaults to data/refactor/candidates/cvs."
        ),
    )
    parser.add_argument(
        "output_path",
        type=Path,
        nargs="?",
        help=(
            "Output file or directory. For directory input this must resolve to a "
            "directory. Defaults to data/refactor/candidates/profiles."
        ),
    )
    parser.add_argument(
        "-n",
        type=positive_int_arg("-n"),
        help="Maximum number of candidate files to process from a directory input.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.input_path is None:
        args.input_path = DEFAULT_CANDIDATE_INPUT_PATH
    if args.output_path is None:
        args.output_path = DEFAULT_CANDIDATE_PROFILE_OUTPUT_PATH
    return args


def _resolve_candidate_input_file(input_path: Path) -> Path:
    if not input_path.exists():
        raise SystemExit(f"candidate input path does not exist: {input_path}")
    if not input_path.is_file():
        raise SystemExit(f"candidate input path must be a file: {input_path}")
    if input_path.suffix.lower() not in _SUPPORTED_CANDIDATE_INPUT_SUFFIXES:
        supported_suffixes = ", ".join(_SUPPORTED_CANDIDATE_INPUT_SUFFIXES)
        raise SystemExit(
            f"candidate input path must point to one of {supported_suffixes}: {input_path}"
        )
    return input_path


def _resolve_directory_inputs(
    directory_path: Path,
    *,
    limit: int | None = None,
) -> list[Path]:
    candidate_paths = sorted(
        path
        for path in directory_path.iterdir()
        if path.is_file()
        and path.suffix.lower() in _SUPPORTED_CANDIDATE_INPUT_SUFFIXES
    )
    if not candidate_paths:
        supported_suffixes = ", ".join(_SUPPORTED_CANDIDATE_INPUT_SUFFIXES)
        raise SystemExit(
            "candidate input directory contains no supported files "
            f"({supported_suffixes}): {directory_path}"
        )
    if limit is not None:
        return candidate_paths[:limit]
    return candidate_paths


def _resolve_input_paths(
    input_path: Path,
    *,
    input_limit: int | None = None,
) -> list[Path]:
    if not input_path.exists():
        raise SystemExit(f"candidate input path does not exist: {input_path}")

    if input_path.is_file():
        return [_resolve_candidate_input_file(input_path)]

    if not input_path.is_dir():
        raise SystemExit(f"candidate input path must be a file or directory: {input_path}")

    return _resolve_directory_inputs(
        input_path,
        limit=input_limit,
    )


def _resolve_output_path_for_input(
    input_path: Path,
    output_path: Path,
) -> Path:
    if output_path.exists():
        if output_path.is_dir():
            return output_path / f"{input_path.stem}.json"
        if output_path.is_file():
            return output_path
        raise SystemExit(f"candidate output path is not a file or directory: {output_path}")

    if output_path.suffix.lower() == ".json":
        return output_path

    return output_path / f"{input_path.stem}.json"


def _resolve_output_directory(output_path: Path) -> Path:
    if output_path.exists():
        if not output_path.is_dir():
            raise SystemExit(
                "candidate output path must be a directory when input path is a directory: "
                f"{output_path}"
            )
        return output_path

    if output_path.suffix.lower() == ".json":
        raise SystemExit(
            "candidate output path must be a directory when input path is a directory: "
            f"{output_path}"
        )

    return output_path


def run_candidate_profiling(
    *,
    input_path: Path,
    output_path: Path = DEFAULT_CANDIDATE_PROFILE_OUTPUT_PATH,
) -> CandidateProfilingResult:
    resolved_input_path = _resolve_candidate_input_file(input_path)
    candidate_text = convert_to_text(resolved_input_path)
    candidate_profile = profile_candidate_text(candidate_text)
    resolved_output_path = _resolve_output_path_for_input(
        resolved_input_path,
        output_path,
    )
    json_io.write_json(
        resolved_output_path,
        candidate_profile.model_dump(mode="json"),
    )
    log(f"wrote file: {resolved_output_path}")
    return CandidateProfilingResult(
        input_path=resolved_input_path,
        output_path=resolved_output_path,
    )


def run_candidate_profiling_for_input_path(
    *,
    input_path: Path,
    output_path: Path = DEFAULT_CANDIDATE_PROFILE_OUTPUT_PATH,
    input_limit: int | None = None,
) -> list[CandidateProfilingResult]:
    input_is_directory = input_path.exists() and input_path.is_dir()
    resolved_input_paths = _resolve_input_paths(
        input_path,
        input_limit=input_limit,
    )

    if input_is_directory:
        _resolve_output_directory(output_path)

    return [
        run_candidate_profiling(
            input_path=resolved_input_path,
            output_path=output_path,
        )
        for resolved_input_path in resolved_input_paths
    ]


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log(f"candidate profiling started: input={args.input_path}")
    results = run_candidate_profiling_for_input_path(
        input_path=args.input_path,
        output_path=args.output_path,
        input_limit=args.n,
    )
    log(
        f"candidate profiling done: input={args.input_path} | "
        f"files={len(results)}"
    )


if __name__ == "__main__":
    main()
