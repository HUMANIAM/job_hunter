from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Any

from shared.html import (
    extract_canonical_url,
    extract_meta_content,
    find_jsonld_nodes_by_type,
    normalize_inline_text,
)


_VANDERLANDE_WORKDAY_HOST = "vanderlande.wd3.myworkdayjobs.com"
_DESCRIPTION_PREFIX_RE = re.compile(
    r"^Job Title\s+.+?\s+Job Description\s+",
    re.IGNORECASE,
)
_SECTION_MARKERS = [
    "About Vanderlande",
    "The role",
    "Your role",
    "What you'll do",
    "What you bring",
    "What we offer",
    "Your application",
    "Diversity statement",
    "Background screening",
    "Aspire. Grow. Achieve. Together",
]


@dataclass(frozen=True)
class VanderlandeJobPosting:
    title: str
    description: str
    canonical_url: str | None = None
    company_name: str | None = None
    job_id: str | None = None
    location_locality: str | None = None
    location_country: str | None = None
    employment_type: str | None = None
    date_posted: str | None = None
    valid_through: str | None = None

    @property
    def location_label(self) -> str | None:
        if self.location_locality and self.location_country:
            return f"{self.location_locality}, {self.location_country}"
        if self.location_locality:
            return self.location_locality
        if self.location_country:
            return self.location_country
        return None


def _nested_mapping(node: Any, *keys: str) -> dict[str, Any] | None:
    current: Any = node
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current if isinstance(current, dict) else None


def _nested_string(node: Any, *keys: str) -> str | None:
    current: Any = node
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    if isinstance(current, str):
        normalized = normalize_inline_text(current)
        if normalized:
            return normalized
    return None


def _job_posting_source_url(raw_html: str) -> str | None:
    return (
        extract_canonical_url(raw_html)
        or extract_meta_content(raw_html, property_name="og:url")
    )


def is_vanderlande_workday_job_html(raw_html: str) -> bool:
    source_url = _job_posting_source_url(raw_html)
    return bool(source_url and _VANDERLANDE_WORKDAY_HOST in source_url)


def extract_vanderlande_job_posting(
    raw_html: str,
) -> VanderlandeJobPosting | None:
    if not is_vanderlande_workday_job_html(raw_html):
        return None

    job_postings = find_jsonld_nodes_by_type(raw_html, "JobPosting")
    if not job_postings:
        return None

    job_posting = job_postings[0]
    job_location = _nested_mapping(job_posting, "jobLocation", "address") or {}

    title = (
        _nested_string(job_posting, "title")
        or _nested_string(job_posting, "identifier", "name")
        or extract_meta_content(raw_html, property_name="og:title")
    )
    description = (
        _nested_string(job_posting, "description")
        or extract_meta_content(raw_html, property_name="og:description")
    )
    if not title or not description:
        return None

    return VanderlandeJobPosting(
        title=title,
        description=description,
        canonical_url=_job_posting_source_url(raw_html),
        company_name=_nested_string(job_posting, "hiringOrganization", "name"),
        job_id=_nested_string(job_posting, "identifier", "value"),
        location_locality=_nested_string(job_location, "addressLocality"),
        location_country=_nested_string(job_location, "addressCountry"),
        employment_type=_nested_string(job_posting, "employmentType"),
        date_posted=_nested_string(job_posting, "datePosted"),
        valid_through=_nested_string(job_posting, "validThrough"),
    )


def _normalize_vanderlande_description(
    description: str,
    title: str,
) -> str:
    normalized = normalize_inline_text(description)
    normalized = _DESCRIPTION_PREFIX_RE.sub("", normalized)
    title_prefix = f"Job Title {title}"
    if normalized.startswith(title_prefix):
        normalized = normalized[len(title_prefix) :].strip()
    if normalized.startswith("Job Description "):
        normalized = normalized[len("Job Description ") :].strip()
    return normalized


def _render_description_lines(description: str, title: str) -> list[str]:
    normalized = _normalize_vanderlande_description(description, title)
    if not normalized:
        return []

    pattern = "|".join(re.escape(marker) for marker in _SECTION_MARKERS)
    segments = [
        normalize_inline_text(segment)
        for segment in re.split(f"(?={pattern})", normalized)
        if normalize_inline_text(segment)
    ]
    if not segments:
        return []

    lines: list[str] = ["h2: Job Description"]
    for segment in segments:
        matched_marker = next(
            (marker for marker in _SECTION_MARKERS if segment.startswith(marker)),
            None,
        )
        if matched_marker is None:
            lines.append(f"p: {segment}")
            continue

        body = segment[len(matched_marker) :].strip(" :")
        lines.append(f"h2: {matched_marker}")
        if body:
            lines.append(f"p: {body}")

    return lines


def render_vanderlande_job_html(raw_html: str) -> tuple[str, str] | None:
    posting = extract_vanderlande_job_posting(raw_html)
    if posting is None:
        return None

    html_parts = [
        "<html>",
        "<head>",
        f"<title>{html.escape(posting.title)}</title>",
        "</head>",
        "<body>",
        f"<h1>{html.escape(posting.title)}</h1>",
    ]

    metadata_pairs = [
        ("Canonical URL", posting.canonical_url),
        ("Job ID", posting.job_id),
        ("Company", posting.company_name),
        ("Location", posting.location_label),
        ("Employment Type", posting.employment_type),
        ("Date Posted", posting.date_posted),
        ("Valid Through", posting.valid_through),
    ]
    html_parts.extend(
        f"<p>{html.escape(label)}: {html.escape(value)}</p>"
        for label, value in metadata_pairs
        if value
    )

    for line in _render_description_lines(posting.description, posting.title):
        tag_name, text = line.split(": ", 1)
        html_parts.append(f"<{tag_name}>{html.escape(text)}</{tag_name}>")

    html_parts.extend(["</body>", "</html>"])
    return posting.title, "\n".join(html_parts)


__all__ = [
    "VanderlandeJobPosting",
    "extract_vanderlande_job_posting",
    "is_vanderlande_workday_job_html",
    "render_vanderlande_job_html",
]
