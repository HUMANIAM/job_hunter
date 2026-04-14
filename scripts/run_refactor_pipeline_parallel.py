#!/usr/bin/env python3
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys
import time
from typing import Sequence


DEFAULT_COMPANIES = ("philips", "canon", "vanderlande")
DEFAULT_CANDIDATE_PROFILE = Path(
    "data/refactor/candidates/profiles/Ibrahim_Saad_CV.json"
)
DEFAULT_JOBS_ROOT = Path("data/refactor/jobs")
DEFAULT_ELIGIBILITY_ROOT = Path("data/refactor/eligibility")
DEFAULT_MAX_RATE_LIMIT_RETRIES = 6
DEFAULT_INITIAL_RETRY_DELAY_SECONDS = 5.0
_HTML_SUFFIX = ".html"
_RATE_LIMIT_MARKERS = (
    "RateLimitError",
    "rate_limit_exceeded",
    "429",
)


@dataclass(frozen=True)
class CompanyRunResult:
    company: str
    returncode: int
    log_path: Path


@dataclass(frozen=True)
class CommandRunResult:
    returncode: int
    output: str


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run job profiling (pre,ext) and eligibility in parallel across "
            "multiple companies."
        )
    )
    parser.add_argument(
        "companies",
        nargs="*",
        default=list(DEFAULT_COMPANIES),
        help=(
            "Company slugs under data/refactor/jobs/. "
            "Defaults to philips canon vanderlande."
        ),
    )
    parser.add_argument(
        "--candidate-profile",
        type=Path,
        default=DEFAULT_CANDIDATE_PROFILE,
        help=(
            "Candidate profile JSON path. "
            "Defaults to data/refactor/candidates/profiles/Ibrahim_Saad_CV.json."
        ),
    )
    parser.add_argument(
        "--jobs-root",
        type=Path,
        default=DEFAULT_JOBS_ROOT,
        help="Root directory containing per-company html/preprocessing/profile data.",
    )
    parser.add_argument(
        "--eligibility-root",
        type=Path,
        default=DEFAULT_ELIGIBILITY_ROOT,
        help="Root directory for eligibility outputs.",
    )
    parser.add_argument(
        "-n",
        type=int,
        help="Optional file limit passed through to both profiling and eligibility CLIs.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        help="Maximum number of companies to run in parallel. Defaults to company count.",
    )
    parser.add_argument(
        "--max-rate-limit-retries",
        type=int,
        default=DEFAULT_MAX_RATE_LIMIT_RETRIES,
        help=(
            "Maximum retries for extraction or eligibility when the subprocess "
            "fails with an OpenAI rate limit. Defaults to 6."
        ),
    )
    parser.add_argument(
        "--initial-retry-delay-seconds",
        type=float,
        default=DEFAULT_INITIAL_RETRY_DELAY_SECONDS,
        help=(
            "Initial backoff before retrying a rate-limited stage. "
            "Defaults to 5.0 seconds."
        ),
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.max_workers is not None and args.max_workers <= 0:
        raise SystemExit("--max-workers must be greater than zero")
    if args.max_rate_limit_retries < 0:
        raise SystemExit("--max-rate-limit-retries must be zero or greater")
    if args.initial_retry_delay_seconds <= 0:
        raise SystemExit("--initial-retry-delay-seconds must be greater than zero")
    return args


def _run_command(command: list[str], *, cwd: Path, log_file) -> CommandRunResult:
    log_file.write(f"$ {' '.join(command)}\n")
    log_file.flush()
    process = subprocess.Popen(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    output_chunks: list[str] = []
    assert process.stdout is not None
    for output_line in process.stdout:
        output_chunks.append(output_line)
        log_file.write(output_line)
        log_file.flush()
    process.stdout.close()
    returncode = process.wait()
    combined_output = "".join(output_chunks)
    log_file.write(f"[exit {returncode}] {' '.join(command)}\n\n")
    log_file.flush()
    return CommandRunResult(
        returncode=returncode,
        output=combined_output,
    )


def _company_paths(company: str, jobs_root: Path) -> tuple[Path, Path, Path, Path]:
    company_root = jobs_root / company
    html_dir = company_root / "html"
    pre_dir = company_root / "preprocessing"
    profiles_dir = company_root / "vacancy_profiles"
    log_path = company_root / "pipeline.log"
    return html_dir, pre_dir, profiles_dir, log_path


def _list_files(directory: Path, *, suffix: str) -> list[Path]:
    if not directory.exists():
        return []
    return sorted(
        path
        for path in directory.iterdir()
        if path.is_file() and path.suffix.lower() == suffix
    )


def _limited_paths(paths: list[Path], limit: int | None) -> list[Path]:
    if limit is None:
        return paths
    return paths[:limit]


def _target_html_paths(html_dir: Path, input_limit: int | None) -> list[Path]:
    return _limited_paths(_list_files(html_dir, suffix=_HTML_SUFFIX), input_limit)


def _is_rate_limited(output: str) -> bool:
    return any(marker in output for marker in _RATE_LIMIT_MARKERS)


def _run_retryable_stage(
    *,
    stage_label: str,
    command: list[str],
    repo_root: Path,
    log_file,
    max_rate_limit_retries: int,
    initial_retry_delay_seconds: float,
) -> int:
    attempt = 0
    while True:
        log_file.write(f"[stage] {stage_label} attempt={attempt + 1}\n")
        log_file.flush()

        run_result = _run_command(
            command,
            cwd=repo_root,
            log_file=log_file,
        )
        if run_result.returncode == 0:
            return 0

        rate_limited = _is_rate_limited(run_result.output)
        if not rate_limited or attempt >= max_rate_limit_retries:
            if rate_limited:
                log_file.write(
                    f"[error] {stage_label} exhausted rate-limit retries after "
                    f"{attempt + 1} attempt(s)\n"
                )
            else:
                log_file.write(
                    f"[error] {stage_label} failed with a non-rate-limit error\n"
                )
            log_file.flush()
            return run_result.returncode

        delay_seconds = initial_retry_delay_seconds * (2 ** attempt)
        log_file.write(
            f"[retry] {stage_label} rate-limited; sleeping {delay_seconds:.1f}s "
            f"before retry {attempt + 2}\n"
        )
        log_file.flush()
        time.sleep(delay_seconds)
        attempt += 1


def run_company_pipeline(
    *,
    repo_root: Path,
    python_executable: str,
    company: str,
    candidate_profile: Path,
    jobs_root: Path,
    eligibility_root: Path,
    input_limit: int | None,
    max_rate_limit_retries: int,
    initial_retry_delay_seconds: float,
) -> CompanyRunResult:
    html_dir, pre_dir, profiles_dir, log_path = _company_paths(
        company,
        jobs_root,
    )
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with log_path.open("w", encoding="utf-8") as log_file:
        target_html_paths = _target_html_paths(html_dir, input_limit)

        log_file.write(f"[start] company={company}\n")
        log_file.write(f"[paths] html={html_dir} pre={pre_dir} profiles={profiles_dir}\n")
        log_file.write(f"[target] files={len(target_html_paths)}\n")
        log_file.flush()

        preprocessing_command = [
            python_executable,
            "-m",
            "clients.job_profiling.job_profiling_cli",
            str(html_dir),
            "--pipeline",
            "pre",
            "--pre-output-dir",
            str(pre_dir),
        ]
        if input_limit is not None:
            preprocessing_command.extend(["-n", str(input_limit)])

        preprocessing_returncode = _run_retryable_stage(
            stage_label="preprocessing",
            command=preprocessing_command,
            repo_root=repo_root,
            log_file=log_file,
            max_rate_limit_retries=max_rate_limit_retries,
            initial_retry_delay_seconds=initial_retry_delay_seconds,
        )
        if preprocessing_returncode != 0:
            log_file.write("[error] preprocessing failed; skipping extraction and eligibility\n")
            log_file.flush()
            return CompanyRunResult(
                company=company,
                returncode=preprocessing_returncode,
                log_path=log_path,
            )

        extraction_command = [
            python_executable,
            "-m",
            "clients.job_profiling.job_profiling_cli",
            str(pre_dir),
            "--pipeline",
            "ext",
            "--ext-output-dir",
            str(profiles_dir),
        ]
        if input_limit is not None:
            extraction_command.extend(["-n", str(input_limit)])

        extraction_returncode = _run_retryable_stage(
            stage_label="extraction",
            command=extraction_command,
            repo_root=repo_root,
            log_file=log_file,
            max_rate_limit_retries=max_rate_limit_retries,
            initial_retry_delay_seconds=initial_retry_delay_seconds,
        )
        if extraction_returncode != 0:
            log_file.write("[error] extraction failed; skipping eligibility\n")
            log_file.flush()
            return CompanyRunResult(
                company=company,
                returncode=extraction_returncode,
                log_path=log_path,
            )

        eligibility_command = [
            python_executable,
            "-m",
            "clients.eligibility.eligibility_cli",
            str(candidate_profile),
            str(profiles_dir),
            str(eligibility_root),
        ]
        if input_limit is not None:
            eligibility_command.extend(["-n", str(input_limit)])

        eligibility_returncode = _run_retryable_stage(
            stage_label="eligibility",
            command=eligibility_command,
            repo_root=repo_root,
            log_file=log_file,
            max_rate_limit_retries=max_rate_limit_retries,
            initial_retry_delay_seconds=initial_retry_delay_seconds,
        )
        return CompanyRunResult(
            company=company,
            returncode=eligibility_returncode,
            log_path=log_path,
        )


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    candidate_profile = (repo_root / args.candidate_profile).resolve()
    jobs_root = (repo_root / args.jobs_root).resolve()
    eligibility_root = (repo_root / args.eligibility_root).resolve()
    python_executable = sys.executable

    print(
        "launching parallel company pipelines: "
        f"{', '.join(args.companies)}"
    )

    results: list[CompanyRunResult] = []
    max_workers = args.max_workers or len(args.companies)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                run_company_pipeline,
                repo_root=repo_root,
                python_executable=python_executable,
                company=company,
                candidate_profile=candidate_profile,
                jobs_root=jobs_root,
                eligibility_root=eligibility_root,
                input_limit=args.n,
                max_rate_limit_retries=args.max_rate_limit_retries,
                initial_retry_delay_seconds=args.initial_retry_delay_seconds,
            ): company
            for company in args.companies
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            status = "done" if result.returncode == 0 else "failed"
            print(
                f"[{status}] {result.company} "
                f"(exit={result.returncode}) log={result.log_path}"
            )

    failed = [result for result in results if result.returncode != 0]
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
