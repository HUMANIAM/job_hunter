from __future__ import annotations

import hashlib
import re
from pathlib import Path
from typing import Any, Callable

from infra import json_io

DEFAULT_COMPANY_SLUG = "sioux"
BASE_OUTPUT_DIR = Path("data/job_profiles")
BASE_CANDIDATE_PROFILE_DIR = Path("data/candidate_profiles")


def output_dir_for(company_slug: str) -> Path:
    return BASE_OUTPUT_DIR / company_slug


def raw_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "raw"


def evaluated_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "evaluated"


def match_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "match"


def mismatch_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "mismatch"


def ranking_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "rankings"


def match_ranking_output_dir_for(company_slug: str) -> Path:
    return ranking_output_dir_for(company_slug) / "match"


def mismatch_ranking_output_dir_for(company_slug: str) -> Path:
    return ranking_output_dir_for(company_slug) / "mismatch"


def validation_output_path_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / f"jobs_{company_slug}_validation.json"


OUTPUT_DIR = output_dir_for(DEFAULT_COMPANY_SLUG)
RAW_OUTPUT_DIR = raw_output_dir_for(DEFAULT_COMPANY_SLUG)
EVALUATED_OUTPUT_DIR = evaluated_output_dir_for(DEFAULT_COMPANY_SLUG)
MATCH_OUTPUT_DIR = match_output_dir_for(DEFAULT_COMPANY_SLUG)
MISMATCH_OUTPUT_DIR = mismatch_output_dir_for(DEFAULT_COMPANY_SLUG)
RANKING_OUTPUT_DIR = ranking_output_dir_for(DEFAULT_COMPANY_SLUG)
MATCH_RANKING_OUTPUT_DIR = match_ranking_output_dir_for(DEFAULT_COMPANY_SLUG)
MISMATCH_RANKING_OUTPUT_DIR = mismatch_ranking_output_dir_for(DEFAULT_COMPANY_SLUG)
VALIDATION_OUTPUT_PATH = validation_output_path_for(DEFAULT_COMPANY_SLUG)
CANDIDATE_PROFILE_OUTPUT_DIR = BASE_CANDIDATE_PROFILE_DIR


def slugify_job_title(title: str | None) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", (title or "").casefold()).strip("_")
    return normalized or "job"


def job_profile_filename(title: str | None, url: str | None) -> str:
    stem = slugify_job_title(title)
    if not url:
        return f"{stem}.json"

    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stem}__{url_hash}.json"


def job_profile_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return evaluated_output_dir_for(company_slug) / job_profile_filename(title, url)


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


def mismatch_job_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return mismatch_output_dir_for(company_slug) / job_profile_filename(title, url)


def ranking_result_filename(candidate_id: str | None, job_id: str | None) -> str:
    normalized_candidate_id = str(candidate_id or "").strip()
    normalized_job_id = str(job_id or "").strip()
    if not normalized_candidate_id:
        raise ValueError("candidate_id is required for ranking output")
    if not normalized_job_id:
        raise ValueError("job_id is required for ranking output")
    return f"{normalized_candidate_id}_{normalized_job_id}.json"


def ranking_output_path_for(
    company_slug: str,
    status: str,
    candidate_id: str | None,
    job_id: str | None,
) -> Path:
    filename = ranking_result_filename(candidate_id, job_id)
    if status == "match":
        return match_ranking_output_dir_for(company_slug) / filename
    return mismatch_ranking_output_dir_for(company_slug) / filename


def candidate_profile_filename(candidate_id: str | None) -> str:
    normalized_candidate_id = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        str(candidate_id or "").strip(),
    ).strip("._")
    if not normalized_candidate_id:
        raise ValueError("candidate_id is required for candidate profile output")
    return f"{normalized_candidate_id}.json"


def candidate_profile_output_path_for(candidate_id: str | None) -> Path:
    return BASE_CANDIDATE_PROFILE_DIR / candidate_profile_filename(candidate_id)


def _job_identity(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    title = payload.get("title")
    url = payload.get("url")
    return (
        str(title) if title is not None else None,
        str(url) if url is not None else None,
    )


def _ranking_identity(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    candidate_id = payload.get("candidate_id")
    job_id = payload.get("job_id")
    return (
        str(candidate_id) if candidate_id is not None else None,
        str(job_id) if job_id is not None else None,
    )


def _candidate_profile_identity(payload: dict[str, Any]) -> str | None:
    candidate_id = payload.get("candidate_id")
    return str(candidate_id) if candidate_id is not None else None


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


def write_job_profile(
    job_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_payload(
        job_payload,
        company_slug=company_slug,
        path_builder=job_profile_output_path_for,
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


def write_mismatch_job(
    job_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_payload(
        job_payload,
        company_slug=company_slug,
        path_builder=mismatch_job_output_path_for,
        log_message=log_message,
    )


def write_ranking_result(
    ranking_payload: dict[str, Any],
    *,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    candidate_id, job_id = _ranking_identity(ranking_payload)
    status = str(ranking_payload.get("status") or "mismatch")
    output_path = ranking_output_path_for(company_slug, status, candidate_id, job_id)
    json_io.write_json(output_path, ranking_payload)
    if log_message is not None:
        log_message(f"wrote file: {output_path}")
    return output_path


def write_candidate_profile(
    candidate_profile_payload: dict[str, Any],
    *,
    output_path: Path | str | None = None,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    resolved_output_path = (
        Path(output_path)
        if output_path is not None
        else candidate_profile_output_path_for(
            _candidate_profile_identity(candidate_profile_payload)
        )
    )
    json_io.write_json(resolved_output_path, candidate_profile_payload)
    if log_message is not None:
        log_message(f"wrote file: {resolved_output_path}")
    return resolved_output_path
