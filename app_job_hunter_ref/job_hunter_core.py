from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable

from candidate_profile.profile import (
    CandidateProfileDocument,
    compute_source_text_hash,
    extract_profile,
)
from infra.format_conversion import convert_to_text
from reporting import writer as report_writer

DEFAULT_CANDIDATE_PROFILE_DIR = Path("data/candidate_profiles")
DEFAULT_CANDIDATE_PROFILE_PATH = next(
    iter(sorted(DEFAULT_CANDIDATE_PROFILE_DIR.glob("*.json"))),
    DEFAULT_CANDIDATE_PROFILE_DIR / "Ibrahim_Saad_CV.json",
)
DEFAULT_MATCH_SCORE_THRESHOLD = 0.6
DEFAULT_COMPANY_SLUG = "sioux"
_CANDIDATE_PROFILE_FILENAME_RE = re.compile(r"[^A-Za-z0-9._-]+")


def load_candidate_profile(
    candidate_profile_path: Path | str,
    *,
    default_candidate_profile_dir: Path = DEFAULT_CANDIDATE_PROFILE_DIR,
    compute_source_text_hash_fn: Callable[[str], str] = compute_source_text_hash,
    extract_profile_fn: Callable[..., CandidateProfileDocument] = extract_profile,
    convert_to_text_fn: Callable[[Path | str], str] = convert_to_text,
    write_candidate_profile_fn: Callable[..., Any] | None = None,
    log_message: Callable[[str], None] | None = None,
) -> CandidateProfileDocument:
    profile_path = Path(candidate_profile_path)
    if profile_path.suffix.lower() != ".json":
        return _extract_candidate_profile_from_source(
            profile_path,
            default_candidate_profile_dir=default_candidate_profile_dir,
            compute_source_text_hash_fn=compute_source_text_hash_fn,
            extract_profile_fn=extract_profile_fn,
            convert_to_text_fn=convert_to_text_fn,
            write_candidate_profile_fn=write_candidate_profile_fn,
            log_message=log_message,
        )

    with profile_path.open("r", encoding="utf-8") as file_handle:
        payload = json.load(file_handle)

    if "candidate_id" not in payload:
        payload["candidate_id"] = profile_path.stem

    return CandidateProfileDocument.model_validate(payload)


def _candidate_profile_stem(path: Path | str) -> str:
    source_path = Path(path)
    stem = _CANDIDATE_PROFILE_FILENAME_RE.sub("_", source_path.stem).strip("._")
    return stem or "candidate_profile"


def _candidate_profile_output_path_for(
    source_path: Path | str,
    *,
    default_candidate_profile_dir: Path,
) -> Path:
    return default_candidate_profile_dir / f"{_candidate_profile_stem(source_path)}.json"


def _extract_candidate_profile_from_source(
    source_path: Path | str,
    *,
    default_candidate_profile_dir: Path,
    compute_source_text_hash_fn: Callable[[str], str],
    extract_profile_fn: Callable[..., CandidateProfileDocument],
    convert_to_text_fn: Callable[[Path | str], str],
    write_candidate_profile_fn: Callable[..., Any] | None,
    log_message: Callable[[str], None] | None = None,
) -> CandidateProfileDocument:
    resolved_source_path = Path(source_path)
    candidate_profile_path = _candidate_profile_output_path_for(
        resolved_source_path,
        default_candidate_profile_dir=default_candidate_profile_dir,
    )
    profile_text = convert_to_text_fn(resolved_source_path)
    source_text_hash = compute_source_text_hash_fn(profile_text)
    resolved_write_candidate_profile = (
        write_candidate_profile_fn or report_writer.write_candidate_profile
    )

    if candidate_profile_path.exists():
        existing_profile = load_candidate_profile(
            candidate_profile_path,
            default_candidate_profile_dir=default_candidate_profile_dir,
            compute_source_text_hash_fn=compute_source_text_hash_fn,
            extract_profile_fn=extract_profile_fn,
            convert_to_text_fn=convert_to_text_fn,
            write_candidate_profile_fn=resolved_write_candidate_profile,
        )
        if existing_profile.source_text_hash == source_text_hash:
            if log_message is not None:
                log_message(f"reusing candidate profile: {candidate_profile_path}")
            return existing_profile

    candidate_profile = extract_profile_fn(
        profile_text,
        candidate_id=_candidate_profile_stem(resolved_source_path),
    )
    resolved_write_candidate_profile(
        candidate_profile.model_dump(mode="json"),
        output_path=candidate_profile_path,
        log_message=log_message,
    )
    return candidate_profile


def load_job_profile_payload(path: Path | str) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def payload_to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: payload_to_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [payload_to_namespace(item) for item in value]
    return value


def infer_company_slug(job_profile_path: Path) -> str:
    parts = job_profile_path.parts
    for idx, part in enumerate(parts[:-1]):
        if part == "job_profiles" and idx + 1 < len(parts):
            return parts[idx + 1]
    return DEFAULT_COMPANY_SLUG


def _remove_stale_artifact(
    output_path: Path,
    *,
    log_message: Callable[[str], None] | None = None,
) -> None:
    if not output_path.exists():
        return

    output_path.unlink()
    if log_message is not None:
        log_message(f"removed stale file: {output_path}")


def _remove_empty_dir(
    output_dir: Path,
    *,
    log_message: Callable[[str], None] | None = None,
) -> None:
    if not output_dir.exists() or not output_dir.is_dir():
        return
    try:
        output_dir.rmdir()
    except OSError:
        return
    if log_message is not None:
        log_message(f"removed empty dir: {output_dir}")


def _remove_stale_opposite_ranking_artifact(
    *,
    writer: Any,
    company_slug: str,
    ranking_result: dict[str, Any],
    log_message: Callable[[str], None] | None = None,
) -> None:
    candidate_id = ranking_result.get("candidate_id")
    job_id = ranking_result.get("job_id")
    status = ranking_result.get("status")
    opposite_status = "mismatch" if status == "match" else "match"
    _remove_stale_artifact(
        writer.ranking_output_path_for(
            company_slug,
            opposite_status,
            candidate_id,
            job_id,
        ),
        log_message=log_message,
    )


def _remove_legacy_job_decision_artifacts(
    *,
    writer: Any,
    company_slug: str,
    title: str | None,
    url: str | None,
    log_message: Callable[[str], None] | None = None,
) -> None:
    _remove_stale_artifact(
        writer.match_job_output_path_for(company_slug, title, url),
        log_message=log_message,
    )
    _remove_stale_artifact(
        writer.mismatch_job_output_path_for(company_slug, title, url),
        log_message=log_message,
    )
    _remove_empty_dir(
        writer.match_output_dir_for(company_slug),
        log_message=log_message,
    )
    _remove_empty_dir(
        writer.mismatch_output_dir_for(company_slug),
        log_message=log_message,
    )


def rank_and_write_job_artifacts(
    *,
    candidate_profile: CandidateProfileDocument,
    job: Any,
    job_payload: dict[str, Any] | None,
    company_slug: str,
    rank_job_fn: Callable[..., dict[str, Any]],
    writer: Any = report_writer,
    match_score_threshold: float = DEFAULT_MATCH_SCORE_THRESHOLD,
    index: int | None = None,
    log_message: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    ranking_result = rank_job_fn(
        candidate_profile,
        job,
        match_score_threshold=match_score_threshold,
        index=index,
        log_message=log_message,
    )
    writer.write_ranking_result(
        ranking_result,
        company_slug=company_slug,
        log_message=log_message,
    )
    _remove_stale_opposite_ranking_artifact(
        writer=writer,
        company_slug=company_slug,
        ranking_result=ranking_result,
        log_message=log_message,
    )

    resolved_job_payload = (
        dict(job_payload)
        if job_payload is not None
        else asdict(job)
    )
    title = resolved_job_payload.get("title")
    url = resolved_job_payload.get("url")
    _remove_legacy_job_decision_artifacts(
        writer=writer,
        company_slug=company_slug,
        title=title,
        url=url,
        log_message=log_message,
    )

    return ranking_result
