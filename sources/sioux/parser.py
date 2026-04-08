from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from shared.normalizer import normalize_taxonomy_name, normalize_text
from sources.sioux.llm import (
    SiouxLlmExtractionPayload,
    SiouxLlmExtractor,
    get_default_llm_extractor,
)
from sources.sioux.normalizer import normalize_job_tag_key


@dataclass
class SiouxJobDeterministic:
    title: str
    url: str
    disciplines: list[str]
    location: str | None
    team: str | None
    work_experience: str | None
    min_years_experience: int | None
    max_years_experience: int | None
    experience_text: str | None
    educational_background: str | None
    required_degrees: list[str]
    industry_domains: list[str]
    workplace_type: str | None
    fulltime_parttime: str | None
    min_hours_per_week: int | None
    max_hours_per_week: int | None
    remote_policy: str | None
    work_locations_text: str | None
    client_site_required: bool | None
    travel_region: str | None
    recruiter_name: str | None
    recruiter_role: str | None
    recruiter_email: str | None
    recruiter_phone: str | None
    description_text: str


@dataclass
class SiouxJobFeature:
    name: str
    requirement_level: str
    confidence: float
    evidence: list[str]
    source_kind: str


@dataclass
class SiouxJobRestriction:
    value: str
    confidence: float
    evidence: list[str]
    source_kind: str


@dataclass
class SiouxJobSeniority:
    value: str | None
    confidence: float
    evidence: list[str]
    source_kind: str | None


@dataclass
class SiouxJobYearsExperienceRequirement:
    min_years: int | None
    max_years: int | None
    requirement_level: str | None
    confidence: float
    evidence: list[str]
    source_kind: str | None


@dataclass
class SiouxJobConstraint:
    kind: str
    bucket: str
    value: str | None
    min_years: int | None
    confidence: float
    evidence: list[str]
    source_kind: str | None


@dataclass
class SiouxJob:
    job_id: str
    title: str
    url: str
    disciplines: list[str]
    location: str | None
    team: str | None
    work_experience: str | None
    years_experience_requirement: SiouxJobYearsExperienceRequirement
    educational_background: str | None
    required_degrees: list[str]
    skills: list[SiouxJobFeature]
    languages: list[SiouxJobFeature]
    protocols: list[SiouxJobFeature]
    standards: list[SiouxJobFeature]
    industry_domains: list[str]
    domains: list[SiouxJobFeature]
    job_constraints: list[SiouxJobConstraint]
    workplace_type: str | None
    fulltime_parttime: str | None
    min_hours_per_week: int | None
    max_hours_per_week: int | None
    remote_policy: str | None
    work_locations_text: str | None
    client_site_required: bool | None
    travel_region: str | None
    recruiter_name: str | None
    recruiter_role: str | None
    recruiter_email: str | None
    recruiter_phone: str | None
    seniority: SiouxJobSeniority
    restrictions: list[SiouxJobRestriction]
    description_text: str


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
EXPERIENCE_SINGLE_RE = re.compile(
    r"\b(\d+)\s*years?\b",
    re.IGNORECASE,
)
HOURS_RANGE_RE = re.compile(
    r"\b(\d+)\s*(?:-|–|—|to)\s*(\d+)\s*(?:hours?|hrs?)\s*(?:per week|working week)\b",
    re.IGNORECASE,
)
HOURS_SINGLE_RE = re.compile(
    r"\b(\d+)\s*(?:hours?|hrs?)\s*(?:per week|working week)\b",
    re.IGNORECASE,
)
DEGREE_PATTERNS = (
    (
        "Secondary vocational education",
        re.compile(
            r"\b(?:secondary vocational education|secondary vocational|mbo(?:-\d+)?)\b",
            re.IGNORECASE,
        ),
    ),
    ("Associate", re.compile(r"\bassociate(?:'s|’s)?\b", re.IGNORECASE)),
    ("Bachelor", re.compile(r"\bbachelor(?:'s|’s)?\b", re.IGNORECASE)),
    ("Master", re.compile(r"\bmaster(?:'s|’s)?\b", re.IGNORECASE)),
    ("PhD", re.compile(r"\b(?:phd|ph\.d\.|doctorate|doctoral)\b", re.IGNORECASE)),
)
INDUSTRY_PATTERNS = (
    ("Semiconductor", re.compile(r"\bsemiconductor\b", re.IGNORECASE)),
    ("Analytical", re.compile(r"\banalytical\b|\banalytics\b", re.IGNORECASE)),
    ("Medical", re.compile(r"\bmedical\b|\bmedtech\b", re.IGNORECASE)),
    ("Energy", re.compile(r"\benergy\b", re.IGNORECASE)),
    ("Aerospace", re.compile(r"\baerospace\b", re.IGNORECASE)),
    ("Automotive", re.compile(r"\bautomotive\b", re.IGNORECASE)),
    ("Defense", re.compile(r"\bdefen[cs]e\b", re.IGNORECASE)),
    ("Industrial", re.compile(r"\bindustrial\b", re.IGNORECASE)),
    ("High-tech", re.compile(r"\bhigh[- ]tech\b", re.IGNORECASE)),
)
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b")
PHONE_RE = re.compile(r"\+\d[\d ()-]{6,}\d")
RECRUITER_ROLE_START_TOKENS = {
    "senior",
    "talent",
    "recruitment",
    "recruiter",
    "manager",
    "acquisition",
    "advisor",
    "specialist",
    "partner",
    "lead",
}
WORK_LOCATION_RE = re.compile(
    r"(From our .*?)(?:,?\s+you\s+(?:will\s+)?work\b|,?\s+you\s+like\s+to\s+keep\s+yourself\s+busy\s+with\b|$)",
    re.IGNORECASE,
)
TRAVEL_REGION_PATTERNS = (
    re.compile(r"\bmainly in the ([A-Z][A-Za-z0-9' -]+? area)\b"),
    re.compile(r"\bwithin the ([A-Z][A-Za-z0-9' -]+? region(?: and beyond)?)\b"),
    re.compile(r"\bin the ([A-Z][A-Za-z0-9' -]+? region)\b"),
    re.compile(r"\bin (Southern Germany, Austria and Switzerland)\b"),
)
CLIENT_SITE_MARKERS = (
    "clients' sites",
    "clients’ sites",
    "clients' premises",
    "clients’ premises",
    "client sites",
    "client site",
    "customer sites",
    "customer site",
)


def _log(log_message: Callable[[str], None] | None, message: str) -> None:
    if log_message is not None:
        log_message(message)


def compute_job_id(title: str | None, url: str | None) -> str:
    stem = re.sub(r"[^a-z0-9]+", "_", (title or "").casefold()).strip("_") or "job"
    if not url:
        return stem

    url_hash = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stem}__{url_hash}"


def extract_job_tags(page: Page) -> dict[str, str]:
    tags: dict[str, str] = {}
    try:
        tag_nodes = page.locator(".job-tags-wrapper .job-tag")
        tag_count = tag_nodes.count()
    except Exception:
        return tags

    for index in range(tag_count):
        tag_node = tag_nodes.nth(index)
        raw_key = (
            tag_node.get_attribute("data-type") or tag_node.get_attribute("title") or ""
        )
        key = normalize_job_tag_key(raw_key)
        if not key:
            continue

        try:
            value = normalize_text(
                tag_node.locator(".job-tag-value").first.inner_text(timeout=2000)
            )
        except Exception:
            continue

        if value:
            tags[key] = value

    return tags


def parse_job_posting_json_ld_blocks(
    json_ld_blocks: Iterable[str],
) -> dict[str, str | None]:
    metadata: dict[str, str | None] = {
        "location": None,
        "country": None,
        "employment_type": None,
    }

    for json_ld_text in json_ld_blocks:
        try:
            payload = json.loads(json_ld_text)
        except json.JSONDecodeError:
            continue

        nodes = payload if isinstance(payload, list) else [payload]
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if normalize_text(str(node.get("@type", ""))).lower() != "jobposting":
                continue

            job_location = node.get("jobLocation") or {}
            address = (
                job_location.get("address", {})
                if isinstance(job_location, dict)
                else {}
            )
            if isinstance(address, dict):
                locality = normalize_text(str(address.get("addressLocality", "")))
                country = normalize_text(str(address.get("addressCountry", "")))
                metadata["location"] = locality or None
                metadata["country"] = country or None

            employment_type = normalize_text(str(node.get("employmentType", "")))
            metadata["employment_type"] = employment_type or None
            return metadata

    return metadata


def extract_job_posting_metadata(page: Page) -> dict[str, str | None]:
    json_ld_blocks: list[str] = []
    try:
        script_nodes = page.locator("script[type='application/ld+json']")
        script_count = script_nodes.count()
    except Exception:
        return parse_job_posting_json_ld_blocks([])

    for index in range(script_count):
        try:
            script_text = script_nodes.nth(index).inner_text(timeout=2000)
        except Exception:
            continue
        if script_text:
            json_ld_blocks.append(script_text)

    return parse_job_posting_json_ld_blocks(json_ld_blocks)


def resolve_job_metadata(page: Page) -> dict[str, str | None]:
    job_tags = extract_job_tags(page)
    schema_metadata = extract_job_posting_metadata(page)

    return {
        "location": job_tags.get("location") or schema_metadata["location"],
        "country": schema_metadata["country"],
        "educational_background": job_tags.get("education level"),
        "fulltime_parttime": (
            job_tags.get("employment") or schema_metadata["employment_type"]
        ),
    }


def extract_value_by_label(page: Page, label: str) -> str | None:
    try:
        locator = page.locator(f"text='{label}'").first
        if locator.count() == 0:
            return None

        parent = locator.locator("xpath=..")
        block_text = normalize_text(parent.inner_text(timeout=2000))

        if block_text.lower().startswith(label.lower()):
            value = block_text[len(label) :].strip(" :\n\t")
            return value or None

        return None
    except Exception:
        return None


def extract_description_text(page: Page) -> str:
    for selector in ["main", "article", "body"]:
        locator = page.locator(selector).first
        if locator.count() == 0:
            continue
        try:
            text = normalize_text(locator.inner_text(timeout=3000))
            if len(text) > 200:
                return text
        except Exception:
            pass
    return ""


def parse_experience_years(text: str) -> tuple[int | None, int | None]:
    normalized = normalize_text(text)
    if not normalized:
        return None, None

    range_match = EXPERIENCE_RANGE_RE.search(normalized)
    if range_match is not None:
        return int(range_match.group(1)), int(range_match.group(2))

    at_least_match = EXPERIENCE_AT_LEAST_RE.search(normalized)
    if at_least_match is not None:
        return int(at_least_match.group(1)), None

    plus_match = EXPERIENCE_PLUS_RE.search(normalized)
    if plus_match is not None:
        return int(plus_match.group(1)), None

    single_match = EXPERIENCE_SINGLE_RE.search(normalized)
    if single_match is not None:
        years = int(single_match.group(1))
        return years, years

    return None, None


def resolve_experience_fields(
    work_experience: str | None,
    description_text: str,
) -> tuple[int | None, int | None, str | None]:
    candidates: list[str] = []
    if work_experience:
        candidates.append(work_experience)

    sentences = re.split(r"(?<=[.!?])\s+", normalize_text(description_text))
    for sentence in sentences:
        lowered = sentence.lower()
        if "experience" in lowered or "experienced" in lowered:
            candidates.append(sentence)

    if not candidates:
        return None, None, None

    fallback_text = normalize_text(candidates[0]) or None
    for candidate in candidates:
        min_years, max_years = parse_experience_years(candidate)
        if min_years is not None or max_years is not None:
            normalized_candidate = normalize_text(candidate) or candidate
            return min_years, max_years, normalized_candidate

    return None, None, fallback_text


def extract_required_degrees(
    educational_background: str | None,
    description_text: str,
) -> list[str]:
    candidates: list[str] = []
    if educational_background:
        candidates.append(educational_background)
    candidates.append(description_text)

    matches: list[tuple[int, int, str]] = []
    for text_index, candidate in enumerate(candidates):
        normalized = normalize_text(candidate)
        if not normalized:
            continue

        for canonical_degree, pattern in DEGREE_PATTERNS:
            for match in pattern.finditer(normalized):
                matches.append((text_index, match.start(), canonical_degree))

    ordered_degrees: list[str] = []
    seen_degrees: set[str] = set()
    for _text_index, _match_start, canonical_degree in sorted(matches):
        if canonical_degree in seen_degrees:
            continue
        ordered_degrees.append(canonical_degree)
        seen_degrees.add(canonical_degree)

    return ordered_degrees


def extract_industry_domains(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []

    matches: list[tuple[int, str]] = []
    for canonical_domain, pattern in INDUSTRY_PATTERNS:
        for match in pattern.finditer(normalized):
            matches.append((match.start(), canonical_domain))

    ordered_domains: list[str] = []
    seen_domains: set[str] = set()
    for _match_start, canonical_domain in sorted(matches):
        if canonical_domain in seen_domains:
            continue
        ordered_domains.append(canonical_domain)
        seen_domains.add(canonical_domain)

    return ordered_domains


def parse_hours_per_week(text: str) -> tuple[int | None, int | None]:
    normalized = normalize_text(text)
    if not normalized:
        return None, None

    range_match = HOURS_RANGE_RE.search(normalized)
    if range_match is not None:
        return int(range_match.group(1)), int(range_match.group(2))

    single_match = HOURS_SINGLE_RE.search(normalized)
    if single_match is not None:
        hours = int(single_match.group(1))
        return hours, hours

    return None, None


def resolve_remote_policy(
    workplace_type: str | None,
    description_text: str,
) -> str | None:
    normalized_workplace_type = normalize_text(workplace_type or "")
    lowered_workplace_type = normalized_workplace_type.lower()

    if "hybrid" in lowered_workplace_type:
        return "Hybrid"
    if "remote" in lowered_workplace_type:
        return "Remote"
    if any(
        token in lowered_workplace_type
        for token in ("on-site", "onsite", "on site", "office")
    ):
        return "On-site"

    normalized_description = normalize_text(description_text).lower()
    if any(
        phrase in normalized_description
        for phrase in ("fully remote", "100% remote", "remote-first")
    ):
        return "Remote"
    if any(
        phrase in normalized_description
        for phrase in (
            "work from home",
            "working from home",
            "room to work from home",
            "home office",
        )
    ):
        return "Hybrid"
    if any(
        phrase in normalized_description for phrase in ("on-site", "onsite", "on site")
    ):
        return "On-site"

    return None


def extract_work_location_fields(
    description_text: str,
) -> tuple[str | None, bool | None, str | None]:
    normalized = normalize_text(description_text)
    if not normalized:
        return None, None, None

    work_locations_text: str | None = None
    location_match = WORK_LOCATION_RE.search(normalized)
    if location_match is not None:
        work_locations_text = location_match.group(1).strip(" ,.:;")

    location_source = (work_locations_text or normalized).lower()
    client_site_required: bool | None = None
    if any(marker in location_source for marker in CLIENT_SITE_MARKERS):
        client_site_required = True
    elif work_locations_text is not None:
        client_site_required = False

    travel_region: str | None = None
    for pattern in TRAVEL_REGION_PATTERNS:
        match = pattern.search(normalized)
        if match is not None:
            travel_region = match.group(1).strip(" ,.:;")
            break

    return work_locations_text, client_site_required, travel_region


def split_recruiter_identity(text: str) -> tuple[str | None, str | None]:
    normalized = normalize_text(text)
    if not normalized:
        return None, None

    tokens = normalized.split()
    role_start_index: int | None = None
    for index, token in enumerate(tokens):
        if token.lower().strip(".,:;") in RECRUITER_ROLE_START_TOKENS:
            role_start_index = index
            break

    if role_start_index is None:
        return normalized, None

    recruiter_name = " ".join(tokens[:role_start_index]).strip() or None
    recruiter_role = " ".join(tokens[role_start_index:]).strip() or None
    return recruiter_name, recruiter_role


def _infer_requirement_level(text: str | None) -> str | None:
    normalized = normalize_text(text or "").lower()
    if not normalized:
        return None

    preferred_markers = (
        "is a plus",
        "are a plus",
        "nice to have",
        "preferred",
        "preferably",
        "would be nice",
    )
    if any(marker in normalized for marker in preferred_markers):
        return "preferred"
    return "required"


def _build_feature_items(
    values: Iterable[object],
) -> list[SiouxJobFeature]:
    return [
        SiouxJobFeature(
            name=getattr(value, "name"),
            requirement_level=getattr(value, "requirement_level"),
            confidence=getattr(value, "confidence"),
            evidence=list(getattr(value, "evidence")),
            source_kind="llm",
        )
        for value in values
    ]


def _build_restrictions(
    values: Iterable[object],
) -> list[SiouxJobRestriction]:
    return [
        SiouxJobRestriction(
            value=getattr(value, "value"),
            confidence=getattr(value, "confidence"),
            evidence=list(getattr(value, "evidence")),
            source_kind="llm",
        )
        for value in values
    ]


def _build_seniority(value: object) -> SiouxJobSeniority:
    seniority_value = getattr(value, "value")
    return SiouxJobSeniority(
        value=seniority_value,
        confidence=getattr(value, "confidence"),
        evidence=list(getattr(value, "evidence")),
        source_kind="llm" if seniority_value is not None else None,
    )


def _build_years_experience_requirement(
    job: SiouxJobDeterministic,
) -> SiouxJobYearsExperienceRequirement:
    if job.min_years_experience is None and job.max_years_experience is None:
        return SiouxJobYearsExperienceRequirement(
            min_years=None,
            max_years=None,
            requirement_level=None,
            confidence=0.0,
            evidence=[],
            source_kind=None,
        )

    evidence: list[str] = []
    if job.experience_text:
        evidence.append(job.experience_text)
    elif job.work_experience:
        evidence.append(job.work_experience)

    return SiouxJobYearsExperienceRequirement(
        min_years=job.min_years_experience,
        max_years=job.max_years_experience,
        requirement_level=_infer_requirement_level(
            job.experience_text or job.work_experience
        ),
        confidence=0.9,
        evidence=evidence,
        source_kind="regex_text",
    )


def _constraint_value_for_restriction(value: str | None) -> str:
    normalized = normalize_taxonomy_name(value or "")
    if not normalized:
        return "restriction"
    if "citizen" in normalized or "citizenship" in normalized or "nationality" in normalized:
        return "citizenship"
    if any(
        token in normalized
        for token in (
            "security clearance",
            "clearance",
            "controlled technology",
            "export administration regulations",
            "export control",
            "ear",
        )
    ):
        return "controlled_technology"
    if any(
        token in normalized
        for token in (
            "work authorization",
            "work authorisation",
            "legally authorized",
            "legally authorised",
            "visa",
            "sponsorship",
        )
    ):
        return "work_authorization"
    return "restriction"


def _build_job_constraints(
    *,
    skills: list[SiouxJobFeature],
    languages: list[SiouxJobFeature],
    protocols: list[SiouxJobFeature],
    standards: list[SiouxJobFeature],
    domains: list[SiouxJobFeature],
    seniority: SiouxJobSeniority,
    years_experience_requirement: SiouxJobYearsExperienceRequirement,
    restrictions: list[SiouxJobRestriction],
) -> list[SiouxJobConstraint]:
    constraints: list[SiouxJobConstraint] = []
    seen_keys: set[tuple[str, str, str | None, int | None]] = set()

    def append_constraint(
        *,
        kind: str,
        bucket: str,
        value: str | None,
        min_years: int | None,
        confidence: float,
        evidence: list[str],
        source_kind: str | None,
    ) -> None:
        key = (kind, bucket, value, min_years)
        if key in seen_keys:
            return
        seen_keys.add(key)
        constraints.append(
            SiouxJobConstraint(
                kind=kind,
                bucket=bucket,
                value=value,
                min_years=min_years,
                confidence=confidence,
                evidence=list(evidence),
                source_kind=source_kind,
            )
        )

    for bucket_name, items in (
        ("skills", skills),
        ("languages", languages),
        ("protocols", protocols),
        ("standards", standards),
        ("domains", domains),
    ):
        for item in items:
            if item.requirement_level != "required":
                continue
            append_constraint(
                kind="feature",
                bucket=bucket_name,
                value=item.name,
                min_years=None,
                confidence=item.confidence,
                evidence=item.evidence,
                source_kind=item.source_kind,
            )

    if seniority.value is not None:
        append_constraint(
            kind="seniority",
            bucket="seniority",
            value=seniority.value,
            min_years=None,
            confidence=seniority.confidence,
            evidence=seniority.evidence,
            source_kind=seniority.source_kind,
        )

    if (
        years_experience_requirement.min_years is not None
        and years_experience_requirement.requirement_level != "preferred"
    ):
        append_constraint(
            kind="years_experience",
            bucket="years_experience",
            value=None,
            min_years=years_experience_requirement.min_years,
            confidence=years_experience_requirement.confidence,
            evidence=years_experience_requirement.evidence,
            source_kind=years_experience_requirement.source_kind,
        )

    for restriction in restrictions:
        append_constraint(
            kind="restriction",
            bucket="restrictions",
            value=_constraint_value_for_restriction(restriction.value),
            min_years=None,
            confidence=restriction.confidence,
            evidence=restriction.evidence,
            source_kind=restriction.source_kind,
        )

    return constraints


def _summarize_years_experience(
    value: SiouxJobYearsExperienceRequirement,
) -> str:
    return (
        f"min_years={value.min_years!r}, "
        f"max_years={value.max_years!r}, "
        f"level={value.requirement_level!r}, "
        f"source={value.source_kind!r}"
    )


def extract_recruiter_fields(
    description_text: str,
) -> tuple[str | None, str | None, str | None, str | None]:
    normalized = normalize_text(description_text)
    if not normalized:
        return None, None, None, None

    email_match = EMAIL_RE.search(normalized)
    if email_match is None:
        return None, None, None, None

    recruiter_email = email_match.group(0)
    prefix_start = max(0, email_match.start() - 240)
    candidate_window = normalized[prefix_start : email_match.end()].strip()

    phone_match = PHONE_RE.search(candidate_window)
    recruiter_phone = normalize_text(phone_match.group(0)) if phone_match else None

    identity_end = (
        phone_match.start() if phone_match else candidate_window.find(recruiter_email)
    )
    identity_text = candidate_window[:identity_end].strip(" ,.:;")
    gdpr_marker = "gdpr regulations."
    gdpr_index = identity_text.lower().rfind(gdpr_marker)
    if gdpr_index >= 0:
        identity_text = identity_text[gdpr_index + len(gdpr_marker) :].strip(" ,.:;")

    recruiter_name, recruiter_role = split_recruiter_identity(identity_text)
    return recruiter_name, recruiter_role, recruiter_email, recruiter_phone


def fetch_job_deterministic(
    page: Page,
    url: str,
    disciplines: list[str] | None = None,
    log_message: Callable[[str], None] | None = None,
) -> SiouxJobDeterministic | None:
    _log(log_message, f"opening vacancy page: {url}")
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(1000)
    except PlaywrightTimeoutError:
        _log(log_message, f"warn: timeout opening {url}")
        return None

    try:
        title = page.locator("h1").first.inner_text(timeout=3000).strip()
    except Exception:
        _log(log_message, f"warn: could not read title for {url}")
        return None

    metadata = resolve_job_metadata(page)
    description_text = extract_description_text(page)
    work_experience = extract_value_by_label(page, "Work experience")
    (
        min_years_experience,
        max_years_experience,
        experience_text,
    ) = resolve_experience_fields(
        work_experience,
        description_text,
    )

    educational_background = metadata[
        "educational_background"
    ] or extract_value_by_label(page, "Educational background")
    required_degrees = extract_required_degrees(
        educational_background,
        description_text,
    )
    industry_domains = extract_industry_domains(description_text)
    workplace_type = extract_value_by_label(page, "Workplace type")
    min_hours_per_week, max_hours_per_week = parse_hours_per_week(description_text)
    remote_policy = resolve_remote_policy(workplace_type, description_text)
    (
        work_locations_text,
        client_site_required,
        travel_region,
    ) = extract_work_location_fields(description_text)
    (
        recruiter_name,
        recruiter_role,
        recruiter_email,
        recruiter_phone,
    ) = extract_recruiter_fields(description_text)

    return SiouxJobDeterministic(
        title=normalize_text(title),
        url=url,
        disciplines=sorted(disciplines or []),
        location=metadata["location"],
        team=extract_value_by_label(page, "Team"),
        work_experience=work_experience,
        min_years_experience=min_years_experience,
        max_years_experience=max_years_experience,
        experience_text=experience_text,
        educational_background=educational_background,
        required_degrees=required_degrees,
        industry_domains=industry_domains,
        workplace_type=workplace_type,
        fulltime_parttime=(
            metadata["fulltime_parttime"]
            or extract_value_by_label(page, "Fulltime/parttime")
        ),
        min_hours_per_week=min_hours_per_week,
        max_hours_per_week=max_hours_per_week,
        remote_policy=remote_policy,
        work_locations_text=work_locations_text,
        client_site_required=client_site_required,
        travel_region=travel_region,
        recruiter_name=recruiter_name,
        recruiter_role=recruiter_role,
        recruiter_email=recruiter_email,
        recruiter_phone=recruiter_phone,
        description_text=description_text,
    )


def _build_job(
    deterministic_job: SiouxJobDeterministic,
    llm_payload: SiouxLlmExtractionPayload,
) -> SiouxJob:
    years_experience_requirement = _build_years_experience_requirement(deterministic_job)
    skills = _build_feature_items(llm_payload.skills)
    languages = _build_feature_items(llm_payload.languages)
    protocols = _build_feature_items(llm_payload.protocols)
    standards = _build_feature_items(llm_payload.standards)
    domains = _build_feature_items(llm_payload.domains)
    seniority = _build_seniority(llm_payload.seniority)
    restrictions = _build_restrictions(llm_payload.restrictions)

    return SiouxJob(
        job_id=compute_job_id(
            deterministic_job.title,
            deterministic_job.url,
        ),
        title=deterministic_job.title,
        url=deterministic_job.url,
        disciplines=deterministic_job.disciplines,
        location=deterministic_job.location,
        team=deterministic_job.team,
        work_experience=deterministic_job.work_experience,
        years_experience_requirement=years_experience_requirement,
        educational_background=deterministic_job.educational_background,
        required_degrees=deterministic_job.required_degrees,
        skills=skills,
        languages=languages,
        protocols=protocols,
        standards=standards,
        industry_domains=deterministic_job.industry_domains,
        domains=domains,
        job_constraints=_build_job_constraints(
            skills=skills,
            languages=languages,
            protocols=protocols,
            standards=standards,
            domains=domains,
            seniority=seniority,
            years_experience_requirement=years_experience_requirement,
            restrictions=restrictions,
        ),
        workplace_type=deterministic_job.workplace_type,
        fulltime_parttime=deterministic_job.fulltime_parttime,
        min_hours_per_week=deterministic_job.min_hours_per_week,
        max_hours_per_week=deterministic_job.max_hours_per_week,
        remote_policy=deterministic_job.remote_policy,
        work_locations_text=deterministic_job.work_locations_text,
        client_site_required=deterministic_job.client_site_required,
        travel_region=deterministic_job.travel_region,
        recruiter_name=deterministic_job.recruiter_name,
        recruiter_role=deterministic_job.recruiter_role,
        recruiter_email=deterministic_job.recruiter_email,
        recruiter_phone=deterministic_job.recruiter_phone,
        seniority=seniority,
        restrictions=restrictions,
        description_text=deterministic_job.description_text,
    )


def fetch_job(
    page: Page,
    url: str,
    disciplines: list[str] | None = None,
    log_message: Callable[[str], None] | None = None,
    llm_extractor: SiouxLlmExtractor | None = None,
) -> SiouxJob | None:
    deterministic_job = fetch_job_deterministic(
        page,
        url,
        disciplines=disciplines,
        log_message=log_message,
    )
    if deterministic_job is None:
        return None

    extractor = llm_extractor or get_default_llm_extractor()
    llm_payload = extractor.extract(deterministic_job)
    job = _build_job(deterministic_job, llm_payload)

    _log(
        log_message,
        "extracted job: "
        f"title='{job.title}', "
        f"disciplines={job.disciplines}, "
        f"location='{job.location}', "
        f"employment='{job.fulltime_parttime}', "
        f"years_experience=({_summarize_years_experience(job.years_experience_requirement)}), "
        f"languages={len(job.languages)}, "
        f"protocols={len(job.protocols)}, "
        f"standards={len(job.standards)}, "
        f"domains={len(job.domains)}, "
        f"seniority='{job.seniority.value}', "
        f"restrictions={len(job.restrictions)}, "
        f"skills={len(job.skills)}, "
        f"description_len={len(job.description_text)}",
    )
    return job
