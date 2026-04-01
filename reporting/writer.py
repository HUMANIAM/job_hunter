from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Iterable

from infra import json_io

OUTPUT_DIR = Path("data/analysis/sioux")
RAW_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_raw.json"
EVALUATED_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_evaluated.json"
OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux.json"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_validation.json"


def _base_payload(
    *,
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    total_jobs: int,
) -> dict[str, Any]:
    return {
        "fetched_at_unix": int(time.time()),
        "source": source,
        "configured_countries": list(configured_countries),
        "configured_languages": list(configured_languages),
        "total_jobs": total_jobs,
    }


def write_validation_report(
    validation_report: dict[str, Any],
    *,
    log_message: Callable[[str], None] | None = None,
) -> None:
    json_io.write_json(VALIDATION_OUTPUT_PATH, validation_report)
    if log_message is not None:
        log_message(f"wrote file: {VALIDATION_OUTPUT_PATH}")


def write_raw_jobs(
    *,
    jobs: list[dict[str, Any]],
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    payload = _base_payload(
        source=source,
        configured_countries=configured_countries,
        configured_languages=configured_languages,
        total_jobs=len(jobs),
    )
    payload["jobs"] = jobs
    json_io.write_json(RAW_OUTPUT_PATH, payload)
    if log_message is not None:
        log_message(f"wrote file: {RAW_OUTPUT_PATH}")
    return payload


def write_evaluated_jobs(
    *,
    jobs: list[dict[str, Any]],
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    payload = _base_payload(
        source=source,
        configured_countries=configured_countries,
        configured_languages=configured_languages,
        total_jobs=len(jobs),
    )
    payload["jobs"] = jobs
    json_io.write_json(EVALUATED_OUTPUT_PATH, payload)
    if log_message is not None:
        log_message(f"wrote file: {EVALUATED_OUTPUT_PATH}")
    return payload


def write_kept_jobs(
    *,
    jobs: list[dict[str, Any]],
    total_jobs: int,
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    payload = _base_payload(
        source=source,
        configured_countries=configured_countries,
        configured_languages=configured_languages,
        total_jobs=total_jobs,
    )
    payload["relevant_jobs"] = len(jobs)
    payload["jobs"] = jobs
    json_io.write_json(OUTPUT_PATH, payload)
    if log_message is not None:
        log_message(f"wrote file: {OUTPUT_PATH}")
    return payload
