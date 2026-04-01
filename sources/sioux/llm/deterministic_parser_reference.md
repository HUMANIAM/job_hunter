# Deterministic Parser Spec and Reference Code

This parser intentionally handles **only confident deterministic fields**.
It does **not** try to classify required vs preferred skills.
That ambiguity is delegated to the LLM.

Use this parser before the LLM step.

## Deterministic Scope

Keep in parser:
- title
- url
- disciplines
- location
- team
- work_experience
- min_years_experience
- max_years_experience
- experience_text
- educational_background
- required_degrees
- industry_domains
- workplace_type
- fulltime_parttime
- min_hours_per_week
- max_hours_per_week
- remote_policy
- work_locations_text
- client_site_required
- travel_region
- recruiter_name
- recruiter_role
- recruiter_email
- recruiter_phone
- description_text

Move out of parser and into LLM:
- required_skills
- preferred_skills
- required_languages
- preferred_languages
- required_protocols
- preferred_protocols
- required_standards
- preferred_standards
- required_domains
- preferred_domains
- restrictions
- seniority_hint

## Reference Code

```python
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

from shared.normalizer import normalize_text
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
    ("Secondary vocational education", re.compile(r"\b(?:secondary vocational education|secondary vocational|mbo(?:-\d+)?)\b", re.IGNORECASE)),
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
            tag_node.get_attribute("data-type")
            or tag_node.get_attribute("title")
            or ""
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
            value = block_text[len(label):].strip(" :\n\t")
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
    if any(token in lowered_workplace_type for token in ("on-site", "onsite", "on site", "office")):
        return "On-site"

    normalized_description = normalize_text(description_text).lower()
    if any(phrase in normalized_description for phrase in ("fully remote", "100% remote", "remote-first")):
        return "Remote"
    if any(phrase in normalized_description for phrase in ("work from home", "working from home", "room to work from home", "home office")):
        return "Hybrid"
    if any(phrase in normalized_description for phrase in ("on-site", "onsite", "on site")):
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

    identity_end = phone_match.start() if phone_match else candidate_window.find(recruiter_email)
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

    educational_background = (
        metadata["educational_background"]
        or extract_value_by_label(page, "Educational background")
    )
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
```

## Integration Note

Then your pipeline becomes:

1. deterministic parser extracts confident fields
2. LLM extracts ambiguous semantic fields
3. merge both into final job object
4. rank deterministically on structured fields
