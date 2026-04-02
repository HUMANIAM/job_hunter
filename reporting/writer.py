from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable

from infra import json_io

DEFAULT_COMPANY_SLUG = "sioux"
BASE_OUTPUT_DIR = Path("data/job_profiles")


def output_dir_for(company_slug: str) -> Path:
    return BASE_OUTPUT_DIR / company_slug


def raw_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "raw"


def evaluated_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "evaluated"


def match_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "match"


def validation_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}_validation.json"


OUTPUT_DIR = output_dir_for(DEFAULT_COMPANY_SLUG)
RAW_OUTPUT_DIR = raw_output_dir_for(DEFAULT_COMPANY_SLUG)
EVALUATED_OUTPUT_DIR = evaluated_output_dir_for(DEFAULT_COMPANY_SLUG)
MATCH_OUTPUT_DIR = match_output_dir_for(DEFAULT_COMPANY_SLUG)
VALIDATION_OUTPUT_PATH = validation_output_path_for(DEFAULT_COMPANY_SLUG)


def slugify_job_title(title: str | None) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (title or "").casefold()).strip("_")
    return normalized or "job"


def job_profile_filename(title: str | None, url: str | None) -> str:
    stem = slugify_job_title(title)
    if not url:
        return f"{stem}.json"

    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stem}__{url_hash}.json"


def raw_job_output_path_for(company_slug: str, title: str | None, url: str | None) -> Path:
    return raw_output_dir_for(company_slug) / job_profile_filename(title, url)


def evaluated_job_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return evaluated_output_dir_for(company_slug) / job_profile_filename(title, url)


def match_job_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return match_output_dir_for(company_slug) / job_profile_filename(title, url)


def _job_identity(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    title = payload.get("title")
    url = payload.get("url")
    return (
        str(title) if title is not None else None,
        str(url) if url is not None else None,
    )


def _write_job_payload(
    payload: dict[str, Any],
    *,
    company_slug: str,
    path_builder: Callable[[str, str | None, str | None], Path],
    log_message: Callable[[str], None] | None = None,
) -> Path:
    title, url = _job_identity(payload)
    output_path = path_builder(company_slug, title, url)
    json_io.write_json(output_path, payload)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return output_path


def write_validation_report(
    validation_report: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    output_path = validation_output_path_for(company_slug)
    json_io.write_json(output_path, validation_report)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return output_path


def write_raw_job(
    job_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_payload(
        job_payload,
        company_slug=company_slug,
        path_builder=raw_job_output_path_for,
        log_message=log_message,
    )


def write_evaluated_job(
    job_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_payload(
        job_payload,
        company_slug=company_slug,
        path_builder=evaluated_job_output_path_for,
        log_message=log_message,
    )


def write_match_job(
    job_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_payload(
        job_payload,
        company_slug=company_slug,
        path_builder=match_job_output_path_for,
        log_message=log_message,
    )
