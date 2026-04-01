from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Callable, Iterable

from infra import json_io

DEFAULT_COMPANY_SLUG = "sioux"
BASE_OUTPUT_DIR = Path("data/analysis")


def output_dir_for(company_slug: str) -> Path:
    return BASE_OUTPUT_DIR / company_slug


def raw_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}_raw.json"


def evaluated_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}_evaluated.json"


def kept_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}.json"


def validation_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}_validation.json"


OUTPUT_DIR = output_dir_for(DEFAULT_COMPANY_SLUG)
RAW_OUTPUT_PATH = raw_output_path_for(DEFAULT_COMPANY_SLUG)
EVALUATED_OUTPUT_PATH = evaluated_output_path_for(DEFAULT_COMPANY_SLUG)
OUTPUT_PATH = kept_output_path_for(DEFAULT_COMPANY_SLUG)
VALIDATION_OUTPUT_PATH = validation_output_path_for(DEFAULT_COMPANY_SLUG)


def _resolve_output_path(
    company_slug: str,
    default_path: Path,
    path_builder: Callable[[str], Path],
) -> Path:
    if company_slug == DEFAULT_COMPANY_SLUG:
        return default_path
    return path_builder(company_slug)


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
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> None:
    output_path = _resolve_output_path(
        company_slug,
        VALIDATION_OUTPUT_PATH,
        validation_output_path_for,
    )
    json_io.write_json(output_path, validation_report)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")


def write_raw_jobs(
    *,
    jobs: list[dict[str, Any]],
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    payload = _base_payload(
        source=source,
        configured_countries=configured_countries,
        configured_languages=configured_languages,
        total_jobs=len(jobs),
    )
    payload["jobs"] = jobs
    output_path = _resolve_output_path(
        company_slug,
        RAW_OUTPUT_PATH,
        raw_output_path_for,
    )
    json_io.write_json(output_path, payload)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return payload


def write_evaluated_jobs(
    *,
    jobs: list[dict[str, Any]],
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    payload = _base_payload(
        source=source,
        configured_countries=configured_countries,
        configured_languages=configured_languages,
        total_jobs=len(jobs),
    )
    payload["jobs"] = jobs
    output_path = _resolve_output_path(
        company_slug,
        EVALUATED_OUTPUT_PATH,
        evaluated_output_path_for,
    )
    json_io.write_json(output_path, payload)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return payload


def write_kept_jobs(
    *,
    jobs: list[dict[str, Any]],
    total_jobs: int,
    source: str,
    configured_countries: Iterable[str],
    configured_languages: Iterable[str],
    company_slug: str = DEFAULT_COMPANY_SLUG,
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
    output_path = _resolve_output_path(
        company_slug,
        OUTPUT_PATH,
        kept_output_path_for,
    )
    json_io.write_json(output_path, payload)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return payload
