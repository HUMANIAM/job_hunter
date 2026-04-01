from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Callable, Iterable

OUTPUT_DIR = Path("data/analysis/sioux")
RAW_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_raw.json"
EVALUATED_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_evaluated.json"
OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux.json"
VALIDATION_OUTPUT_PATH = OUTPUT_DIR / "jobs_sioux_validation.json"


def write_json(
    path: Path | str,
    payload: dict[str, Any],
    log_message: Callable[[str], None] | None = None,
) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file_handle:
        json.dump(payload, file_handle, ensure_ascii=False, indent=2)

    if log_message is not None:
        log_message(f"wrote file: {path}")


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
    write_json(VALIDATION_OUTPUT_PATH, validation_report, log_message)


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
    write_json(RAW_OUTPUT_PATH, payload, log_message)
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
    write_json(EVALUATED_OUTPUT_PATH, payload, log_message)
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
    write_json(OUTPUT_PATH, payload, log_message)
    return payload
