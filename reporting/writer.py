from __future__ import annotations

import hashlib
import html
from html.parser import HTMLParser
import re
from pathlib import Path
from typing import Any, Callable
from urllib.parse import unquote, urlparse

from infra import json_io

DEFAULT_COMPANY_SLUG = "sioux"
BASE_OUTPUT_DIR = Path("data/job_profiles")
BASE_CANDIDATE_PROFILE_DIR = Path("data/candidate_profiles")


def output_dir_for(company_slug: str) -> Path:
    return BASE_OUTPUT_DIR / company_slug


def raw_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "raw"


def raw_structured_output_dir_for(company_slug: str) -> Path:
    return output_dir_for(company_slug) / "raw_structured"


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
RAW_STRUCTURED_OUTPUT_DIR = raw_structured_output_dir_for(DEFAULT_COMPANY_SLUG)
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


class _JobHtmlTitleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta_title: str | None = None
        self.og_title: str | None = None
        self.document_title: str | None = None
        self.first_h1: str | None = None
        self.canonical_url: str | None = None
        self._capture_title = False
        self._capture_h1 = False
        self._title_chunks: list[str] = []
        self._h1_chunks: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = {key.casefold(): (value or "") for key, value in attrs}
        normalized_tag = tag.casefold()

        if normalized_tag == "meta":
            meta_name = attrs_dict.get("name", "").casefold()
            meta_property = attrs_dict.get("property", "").casefold()
            content = attrs_dict.get("content", "").strip()
            if content:
                if meta_property == "og:title" and self.og_title is None:
                    self.og_title = content
                if meta_name == "title" and self.meta_title is None:
                    self.meta_title = content
        elif normalized_tag == "link":
            rel = attrs_dict.get("rel", "").casefold()
            href = attrs_dict.get("href", "").strip()
            if "canonical" in rel and href and self.canonical_url is None:
                self.canonical_url = href
        elif normalized_tag == "title":
            self._capture_title = True
            self._title_chunks = []
        elif normalized_tag == "h1" and self.first_h1 is None:
            self._capture_h1 = True
            self._h1_chunks = []

    def handle_endtag(self, tag: str) -> None:
        normalized_tag = tag.casefold()
        if normalized_tag == "title" and self._capture_title:
            self._capture_title = False
            title_text = "".join(self._title_chunks).strip()
            if title_text and self.document_title is None:
                self.document_title = title_text
        elif normalized_tag == "h1" and self._capture_h1:
            self._capture_h1 = False
            h1_text = "".join(self._h1_chunks).strip()
            if h1_text and self.first_h1 is None:
                self.first_h1 = h1_text

    def handle_data(self, data: str) -> None:
        if self._capture_title:
            self._title_chunks.append(data)
        if self._capture_h1:
            self._h1_chunks.append(data)


def _normalized_non_empty_text(value: str | None) -> str | None:
    normalized = re.sub(r"\s+", " ", html.unescape(value or "")).strip()
    return normalized or None


def _title_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed_url = urlparse(url)
    path_segments = [segment for segment in parsed_url.path.split("/") if segment]
    if not path_segments:
        return None

    candidate = unquote(path_segments[-1])
    if "_" in candidate:
        candidate = candidate.split("_", 1)[0]
    candidate = re.sub(r"[-_]+", " ", candidate)
    candidate = re.sub(r"\s+", " ", candidate).strip()
    return candidate or None


def best_job_title(
    title: str | None,
    *,
    url: str | None = None,
    html_content: str | None = None,
) -> str | None:
    normalized_title = _normalized_non_empty_text(title)
    if normalized_title:
        return normalized_title

    if html_content:
        parser = _JobHtmlTitleParser()
        parser.feed(html_content)
        for candidate in (
            parser.og_title,
            parser.meta_title,
            parser.document_title,
            parser.first_h1,
            _title_from_url(parser.canonical_url),
        ):
            normalized_candidate = _normalized_non_empty_text(candidate)
            if normalized_candidate:
                return normalized_candidate

    return _title_from_url(url)


def job_profile_filename(title: str | None, url: str | None) -> str:
    stem = slugify_job_title(title)
    if not url:
        return f"{stem}.json"

    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stem}__{url_hash}.json"


def raw_html_filename(
    title: str | None,
    url: str | None,
    *,
    html_content: str | None = None,
) -> str:
    return job_profile_filename(
        best_job_title(title, url=url, html_content=html_content),
        url,
    ).replace(".json", ".html")


def job_profile_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return evaluated_output_dir_for(company_slug) / job_profile_filename(title, url)


def raw_job_output_path_for(company_slug: str, title: str | None, url: str | None) -> Path:
    return raw_structured_output_dir_for(company_slug) / job_profile_filename(title, url)


def raw_html_output_path_for(
    company_slug: str,
    title: str | None,
    url: str | None,
) -> Path:
    return raw_output_dir_for(company_slug) / raw_html_filename(title, url)


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


def _write_job_text(
    text: str,
    *,
    company_slug: str,
    title: str | None,
    url: str | None,
    path_builder: Callable[[str, str | None, str | None], Path],
    log_message: Callable[[str], None] | None = None,
) -> Path:
    output_path = path_builder(company_slug, title, url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8")
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


def write_raw_html(
    html_content: str,
    *,
    title: str | None,
    url: str | None,
    company_slug: str = DEFAULT_COMPANY_SLUG,
    log_message: Callable[[str], None] | None = None,
) -> Path:
    return _write_job_text(
        html_content,
        company_slug=company_slug,
        title=title,
        url=url,
        path_builder=raw_html_output_path_for,
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
