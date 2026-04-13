#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this CLI as a module: python -m clients.eligibility.eligibility_cli ..."
    )

from clients.candidate_profiling.candidate_profile_model import CandidateProfile
from clients.eligibility.eligibilty import evaluate_eligibility
from clients.job_profiling.profiling.job_profile_model import VacancyProfile
from infra import json_io
from infra.logging import log
from shared.cli import positive_int_arg

DEFAULT_CANDIDATE_PROFILE_INPUT_PATH = Path(
    "data/refactor/candidates/profiles/Ibrahim_Saad_CV.json"
)
DEFAULT_VACANCY_PROFILE_INPUT_PATH = Path("data/refactor/jobs/sioux/vacancy_profiles")
DEFAULT_ELIGIBILITY_OUTPUT_PATH = Path("data/refactor/eligibility")
_SUPPORTED_PROFILE_SUFFIXES = (".json",)


@dataclass
class EligibilityResult:
    candidate_profile_path: Path
    vacancy_profile_path: Path
    output_path: Path


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a candidate profile against a vacancy profile file or directory "
            "of vacancy profiles."
        )
    )
    parser.add_argument(
        "candidate_profile_path",
        type=Path,
        nargs="?",
        help=(
            "Candidate profile JSON path. Defaults to "
            "data/refactor/candidates/profiles/Ibrahim_Saad_CV.json."
        ),
    )
    parser.add_argument(
        "vacancy_profile_input_path",
        type=Path,
        nargs="?",
        help=(
            "Vacancy profile JSON file or directory. Defaults to "
            "data/refactor/jobs/sioux/vacancy_profiles."
        ),
    )
    parser.add_argument(
        "output_path",
        type=Path,
        nargs="?",
        help=(
            "Eligibility output root directory. Defaults to "
            "data/refactor/eligibility."
        ),
    )
    parser.add_argument(
        "-n",
        type=positive_int_arg("-n"),
        help="Maximum number of vacancy profile files to process from a directory input.",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.candidate_profile_path is None:
        args.candidate_profile_path = DEFAULT_CANDIDATE_PROFILE_INPUT_PATH
    if args.vacancy_profile_input_path is None:
        args.vacancy_profile_input_path = DEFAULT_VACANCY_PROFILE_INPUT_PATH
    if args.output_path is None:
        args.output_path = DEFAULT_ELIGIBILITY_OUTPUT_PATH
    return args


def _resolve_candidate_profile_path(candidate_profile_path: Path) -> Path:
    if not candidate_profile_path.exists():
        raise SystemExit(
            f"candidate profile path does not exist: {candidate_profile_path}"
        )
    if not candidate_profile_path.is_file():
        raise SystemExit(
            f"candidate profile path must be a file: {candidate_profile_path}"
        )
    if candidate_profile_path.suffix.lower() not in _SUPPORTED_PROFILE_SUFFIXES:
        raise SystemExit(
            "candidate profile path must point to a .json file: "
            f"{candidate_profile_path}"
        )
    return candidate_profile_path


def _resolve_vacancy_profile_file(vacancy_profile_path: Path) -> Path:
    if not vacancy_profile_path.exists():
        raise SystemExit(
            f"vacancy profile path does not exist: {vacancy_profile_path}"
        )
    if not vacancy_profile_path.is_file():
        raise SystemExit(
            f"vacancy profile path must be a file: {vacancy_profile_path}"
        )
    if vacancy_profile_path.suffix.lower() not in _SUPPORTED_PROFILE_SUFFIXES:
        raise SystemExit(
            f"vacancy profile path must point to a .json file: {vacancy_profile_path}"
        )
    return vacancy_profile_path


def _resolve_directory_inputs(
    directory_path: Path,
    *,
    limit: int | None = None,
) -> list[Path]:
    vacancy_profile_paths = sorted(
        path
        for path in directory_path.iterdir()
        if path.is_file() and path.suffix.lower() in _SUPPORTED_PROFILE_SUFFIXES
    )
    if not vacancy_profile_paths:
        raise SystemExit(
            "vacancy profile input directory contains no .json files: "
            f"{directory_path}"
        )
    if limit is not None:
        return vacancy_profile_paths[:limit]
    return vacancy_profile_paths


def _resolve_vacancy_profile_input_paths(
    vacancy_profile_input_path: Path,
    *,
    input_limit: int | None = None,
) -> list[Path]:
    if not vacancy_profile_input_path.exists():
        raise SystemExit(
            "vacancy profile input path does not exist: "
            f"{vacancy_profile_input_path}"
        )

    if vacancy_profile_input_path.is_file():
        return [_resolve_vacancy_profile_file(vacancy_profile_input_path)]

    if not vacancy_profile_input_path.is_dir():
        raise SystemExit(
            "vacancy profile input path must be a file or directory: "
            f"{vacancy_profile_input_path}"
        )

    return _resolve_directory_inputs(
        vacancy_profile_input_path,
        limit=input_limit,
    )


def _resolve_output_root(output_path: Path) -> Path:
    if output_path.exists():
        if not output_path.is_dir():
            raise SystemExit(f"eligibility output path must be a directory: {output_path}")
        return output_path

    if output_path.suffix.lower() == ".json":
        raise SystemExit(f"eligibility output path must be a directory: {output_path}")

    return output_path


def _load_candidate_profile(candidate_profile_path: Path) -> CandidateProfile:
    payload = json.loads(candidate_profile_path.read_text(encoding="utf-8"))
    return CandidateProfile.model_validate(payload)


def _load_vacancy_profile(vacancy_profile_path: Path) -> VacancyProfile:
    payload = json.loads(vacancy_profile_path.read_text(encoding="utf-8"))
    return VacancyProfile.model_validate(payload)


def _output_path_for(
    candidate_profile_path: Path,
    decision: str,
    company_name: str,
    vacancy_profile_path: Path,
    output_root: Path,
) -> Path:
    return (
        output_root
        / candidate_profile_path.stem
        / decision
        / company_name
        / vacancy_profile_path.name
    )


def _company_name_for(vacancy_profile_path: Path) -> str:
    if vacancy_profile_path.parent.name == "vacancy_profiles":
        return vacancy_profile_path.parent.parent.name
    return vacancy_profile_path.parent.name


def _write_eligibility_result(
    *,
    candidate_profile_path: Path,
    vacancy_profile_path: Path,
    output_root: Path,
    eligibility: EligibilityResponse,
) -> Path:
    output_path = _output_path_for(
        candidate_profile_path,
        eligibility.decision,
        _company_name_for(vacancy_profile_path),
        vacancy_profile_path,
        output_root,
    )
    json_io.write_json(
        output_path,
        eligibility.model_dump(mode="json"),
    )
    log(f"wrote file: {output_path}")
    return output_path


def _run_loaded_eligibility(
    *,
    candidate_profile_path: Path,
    candidate_profile: CandidateProfile,
    vacancy_profile_path: Path,
    output_root: Path,
) -> EligibilityResult:
    vacancy_profile = _load_vacancy_profile(vacancy_profile_path)
    eligibility = evaluate_eligibility(candidate_profile, vacancy_profile)
    output_path = _write_eligibility_result(
        candidate_profile_path=candidate_profile_path,
        vacancy_profile_path=vacancy_profile_path,
        output_root=output_root,
        eligibility=eligibility,
    )
    return EligibilityResult(
        candidate_profile_path=candidate_profile_path,
        vacancy_profile_path=vacancy_profile_path,
        output_path=output_path,
    )


def run_eligibility(
    *,
    candidate_profile_path: Path,
    vacancy_profile_path: Path,
    output_path: Path = DEFAULT_ELIGIBILITY_OUTPUT_PATH,
) -> EligibilityResult:
    resolved_candidate_profile_path = _resolve_candidate_profile_path(
        candidate_profile_path
    )
    resolved_vacancy_profile_path = _resolve_vacancy_profile_file(vacancy_profile_path)
    candidate_profile = _load_candidate_profile(resolved_candidate_profile_path)
    output_root = _resolve_output_root(output_path)
    return _run_loaded_eligibility(
        candidate_profile_path=resolved_candidate_profile_path,
        candidate_profile=candidate_profile,
        vacancy_profile_path=resolved_vacancy_profile_path,
        output_root=output_root,
    )


def run_eligibility_for_input_path(
    *,
    candidate_profile_path: Path,
    vacancy_profile_input_path: Path,
    output_path: Path = DEFAULT_ELIGIBILITY_OUTPUT_PATH,
    input_limit: int | None = None,
) -> list[EligibilityResult]:
    resolved_candidate_profile_path = _resolve_candidate_profile_path(
        candidate_profile_path
    )
    resolved_vacancy_profile_paths = _resolve_vacancy_profile_input_paths(
        vacancy_profile_input_path,
        input_limit=input_limit,
    )
    candidate_profile = _load_candidate_profile(resolved_candidate_profile_path)
    output_root = _resolve_output_root(output_path)
    return [
        _run_loaded_eligibility(
            candidate_profile_path=resolved_candidate_profile_path,
            candidate_profile=candidate_profile,
            vacancy_profile_path=resolved_vacancy_profile_path,
            output_root=output_root,
        )
        for resolved_vacancy_profile_path in resolved_vacancy_profile_paths
    ]


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    log(
        "eligibility evaluation started: "
        f"candidate={args.candidate_profile_path} | "
        f"vacancies={args.vacancy_profile_input_path}"
    )
    results = run_eligibility_for_input_path(
        candidate_profile_path=args.candidate_profile_path,
        vacancy_profile_input_path=args.vacancy_profile_input_path,
        output_path=args.output_path,
        input_limit=args.n,
    )
    log(
        "eligibility evaluation done: "
        f"candidate={args.candidate_profile_path} | files={len(results)}"
    )


if __name__ == "__main__":
    main()
