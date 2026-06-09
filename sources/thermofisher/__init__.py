from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from html import unescape
from typing import Any, Callable

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from shared.normalizer import normalize_text
from sources.base import SourceDefinition, SourceRetrievalResult
from sources.thermofisher import adapter as thermofisher_adapter

JSON_LD_PATTERN = re.compile(
    r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>",
    re.I | re.S,
)
OG_TITLE_PATTERN = re.compile(
    r'<meta\s+name="title"\s+property="og:title"\s+content="([^"]+)"',
    re.I,
)
OG_DESCRIPTION_PATTERN = re.compile(
    r'<meta\s+name="description"\s+property="og:description"\s+content="([^"]+)"',
    re.I,
)
REQ_ID_PATTERN = re.compile(r"\bR-\d+\b")
EXPERIENCE_RANGE_RE = re.compile(
    r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*years?\b",
    re.IGNORECASE,
)
EXPERIENCE_AT_LEAST_RE = re.compile(
    r"\b(?:at least|minimum of|min\.?)\s*(\d+)\s*years?\b",
    re.IGNORECASE,
)
EXPERIENCE_PLUS_RE = re.compile(
    r"\b(\d+)\+\s*years?\b",
    re.IGNORECASE,
)


@dataclass
class ThermoFisherJobFeature:
    name: str
    requirement_level: str
    confidence: float
    evidence: list[str]
    source_kind: str


@dataclass
class ThermoFisherJobRestriction:
    value: str
    confidence: float
    evidence: list[str]
    source_kind: str


@dataclass
class ThermoFisherJobSeniority:
    value: str | None
    confidence: float
    evidence: list[str]
    source_kind: str | None


@dataclass
class ThermoFisherJobYearsExperienceRequirement:
    min_years: int | None
    max_years: int | None
    requirement_level: str | None
    confidence: float
    evidence: list[str]
    source_kind: str | None


@dataclass
class ThermoFisherJob:
    job_id: str
    title: str
    url: str
    disciplines: list[str]
    location: str | None
    country: str | None
    fulltime_parttime: str | None
    workplace_type: str | None
    remote_policy: str | None
    description_text: str
    skills: list[ThermoFisherJobFeature] = field(default_factory=list)
    languages: list[ThermoFisherJobFeature] = field(default_factory=list)
    protocols: list[ThermoFisherJobFeature] = field(default_factory=list)
    standards: list[ThermoFisherJobFeature] = field(default_factory=list)
    domains: list[ThermoFisherJobFeature] = field(default_factory=list)
    seniority: ThermoFisherJobSeniority = field(
        default_factory=lambda: ThermoFisherJobSeniority(
            value=None,
            confidence=0.0,
            evidence=[],
            source_kind=None,
        )
    )
    years_experience_requirement: ThermoFisherJobYearsExperienceRequirement = field(
        default_factory=lambda: ThermoFisherJobYearsExperienceRequirement(
            min_years=None,
            max_years=None,
            requirement_level=None,
            confidence=0.0,
            evidence=[],
            source_kind=None,
        )
    )
    job_constraints: list[dict[str, object]] = field(default_factory=list)
    restrictions: list[ThermoFisherJobRestriction] = field(default_factory=list)


def _log(log_message: Callable[[str], None] | None, message: str) -> None:
    if log_message is not None:
        log_message(message)


def _normalize_optional_text(value: object | None) -> str | None:
    if value is None:
        return None

    normalized = normalize_text(unescape(str(value)))
    return normalized or None


def _extract_json_ld_job_posting(html: str) -> dict[str, Any]:
    for match in JSON_LD_PATTERN.finditer(html):
        try:
            payload = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue

        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue

            node_type = _normalize_optional_text(node.get("@type"))
            if node_type and node_type.casefold() != "jobposting":
                continue

            if "title" in node or "description" in node or "identifier" in node:
                return node

    return {}


def _extract_meta_content(pattern: re.Pattern[str], html: str) -> str | None:
    match = pattern.search(html)
    if match is None:
        return None

    return _normalize_optional_text(match.group(1))


def _extract_job_id(url: str, payload: dict[str, Any]) -> str:
    identifier = payload.get("identifier")
    if isinstance(identifier, dict):
        value = _normalize_optional_text(identifier.get("value"))
        if value:
            return value

    match = REQ_ID_PATTERN.search(url)
    if match is not None:
        return match.group(0)

    raise RuntimeError(f"Could not determine Thermo Fisher requisition id for {url}.")


def _normalize_location(
    locality: str | None,
    remote_country: str | None,
    workplace_type: str | None,
) -> str | None:
    if locality:
        parts = [normalize_text(part) for part in locality.split(" - ") if normalize_text(part)]
        if len(parts) >= 2:
            country = parts[0]
            city = parts[1]
            if city.casefold() == "remote":
                return f"Remote, {country}"
            return f"{city}, {country}"
        return locality

    if workplace_type == "remote" and remote_country:
        return f"Remote, {remote_country}"

    return remote_country


def _derive_seniority(title: str) -> ThermoFisherJobSeniority:
    normalized_title = title.casefold()
    value = None
    if re.search(r"\bprincipal\b", normalized_title):
        value = "principal"
    elif re.search(r"\bstaff\b", normalized_title):
        value = "staff"
    elif re.search(r"\blead\b", normalized_title):
        value = "lead"
    elif re.search(r"\bsenior\b|\bsr\b", normalized_title):
        value = "senior"

    return ThermoFisherJobSeniority(
        value=value,
        confidence=0.6 if value is not None else 0.0,
        evidence=[title] if value is not None else [],
        source_kind="title" if value is not None else None,
    )


def _derive_years_experience(
    description_text: str,
) -> ThermoFisherJobYearsExperienceRequirement:
    normalized_description = normalize_text(description_text)
    for pattern in (EXPERIENCE_RANGE_RE, EXPERIENCE_AT_LEAST_RE, EXPERIENCE_PLUS_RE):
        match = pattern.search(normalized_description)
        if match is None:
            continue

        if pattern is EXPERIENCE_RANGE_RE:
            min_years = int(match.group(1))
            max_years = int(match.group(2))
        else:
            min_years = int(match.group(1))
            max_years = None

        return ThermoFisherJobYearsExperienceRequirement(
            min_years=min_years,
            max_years=max_years,
            requirement_level="required",
            confidence=0.5,
            evidence=[match.group(0)],
            source_kind="description_text",
        )

    return ThermoFisherJobYearsExperienceRequirement(
        min_years=None,
        max_years=None,
        requirement_level=None,
        confidence=0.0,
        evidence=[],
        source_kind=None,
    )


def _fetch_job(
    page: Page,
    url: str,
    disciplines: list[str] | None = None,
    log_message: Callable[[str], None] | None = None,
) -> ThermoFisherJob | None:
    _log(log_message, f"opening vacancy page: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(500)
    except PlaywrightTimeoutError:
        _log(log_message, f"warn: timeout opening {url}")
        return None

    html = page.content()
    payload = _extract_json_ld_job_posting(html)

    title = _normalize_optional_text(payload.get("title")) or _extract_meta_content(
        OG_TITLE_PATTERN,
        html,
    )
    description_text = _normalize_optional_text(
        payload.get("description")
    ) or _extract_meta_content(
        OG_DESCRIPTION_PATTERN,
        html,
    )
    if title is None:
        _log(log_message, f"warn: could not read title for {url}")
        return None
    if description_text is None:
        _log(log_message, f"warn: could not read description for {url}")
        return None

    job_location = payload.get("jobLocation")
    address = job_location.get("address") if isinstance(job_location, dict) else {}
    locality = _normalize_optional_text(
        address.get("addressLocality") if isinstance(address, dict) else None
    )
    country = _normalize_optional_text(
        address.get("addressCountry") if isinstance(address, dict) else None
    )
    applicant_location_requirements = payload.get("applicantLocationRequirements")
    remote_country = _normalize_optional_text(
        applicant_location_requirements.get("name")
        if isinstance(applicant_location_requirements, dict)
        else None
    )

    job_location_type = _normalize_optional_text(payload.get("jobLocationType"))
    workplace_type = (
        "remote"
        if job_location_type and job_location_type.casefold() == "telecommute"
        else None
    )
    remote_policy = workplace_type
    fulltime_parttime = _normalize_optional_text(
        str(payload.get("employmentType")).replace("_", " ")
        if payload.get("employmentType") is not None
        else None
    )

    job = ThermoFisherJob(
        job_id=_extract_job_id(url, payload),
        title=title,
        url=url,
        disciplines=sorted(disciplines or []),
        location=_normalize_location(locality, remote_country, workplace_type),
        country=country or remote_country,
        fulltime_parttime=fulltime_parttime.title() if fulltime_parttime else None,
        workplace_type=workplace_type,
        remote_policy=remote_policy,
        description_text=description_text,
        seniority=_derive_seniority(title),
        years_experience_requirement=_derive_years_experience(description_text),
    )

    _log(
        log_message,
        "extracted job: "
        f"title='{job.title}', "
        f"location='{job.location}', "
        f"employment='{job.fulltime_parttime}', "
        f"description_len={len(job.description_text)}",
    )
    return job


class ThermoFisherSourceAdapter:
    def retrieve_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> SourceRetrievalResult:
        retrieval = thermofisher_adapter.retrieve_thermofisher_job_links(
            browser,
            job_limit=job_limit,
        )
        return SourceRetrievalResult(
            job_links=retrieval.job_links,
            discipline_map=retrieval.discipline_map,
            validation_report=retrieval.validation_report,
        )

    def log_validation_report(self, report: dict[str, Any]) -> None:
        thermofisher_adapter.log_collection_validation_report(report)


class ThermoFisherSourceParser:
    def fetch_raw_job(
        self,
        page: Page,
        url: str,
        disciplines: list[str] | None = None,
        log_message: Callable[[str], None] | None = None,
    ) -> ThermoFisherJob | None:
        return _fetch_job(page, url, disciplines, log_message)

    def fetch_job(
        self,
        page: Page,
        url: str,
        disciplines: list[str] | None = None,
        log_message: Callable[[str], None] | None = None,
    ) -> ThermoFisherJob | None:
        return _fetch_job(page, url, disciplines, log_message)


THERMOFISHER_SOURCE = SourceDefinition(
    company_slug="thermofisher",
    source_url=thermofisher_adapter.START_URL,
    configured_countries=thermofisher_adapter.TARGET_COUNTRIES,
    configured_languages=thermofisher_adapter.TARGET_LANGUAGES,
    adapter=ThermoFisherSourceAdapter(),
    parser=ThermoFisherSourceParser(),
)
