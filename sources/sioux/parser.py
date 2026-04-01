from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Callable, Iterable

from playwright.sync_api import Page
from playwright.sync_api import (
    TimeoutError as PlaywrightTimeoutError,
)


@dataclass
class SiouxJob:
    title: str
    url: str
    disciplines: list[str]
    location: str | None
    team: str | None
    work_experience: str | None
    educational_background: str | None
    workplace_type: str | None
    fulltime_parttime: str | None
    description_text: str


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_job_tag_key(value: str) -> str:
    return normalize_text(value).lower()


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


def fetch_job(
    page: Page,
    url: str,
    disciplines: list[str] | None = None,
    log_message: Callable[[str], None] | None = None,
) -> SiouxJob | None:
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

    job = SiouxJob(
        title=normalize_text(title),
        url=url,
        disciplines=sorted(disciplines or []),
        location=metadata["location"],
        team=extract_value_by_label(page, "Team"),
        work_experience=extract_value_by_label(page, "Work experience"),
        educational_background=(
            metadata["educational_background"]
            or extract_value_by_label(page, "Educational background")
        ),
        workplace_type=extract_value_by_label(page, "Workplace type"),
        fulltime_parttime=(
            metadata["fulltime_parttime"]
            or extract_value_by_label(page, "Fulltime/parttime")
        ),
        description_text=description_text,
    )

    _log(
        log_message,
        "extracted job: "
        f"title='{job.title}', "
        f"disciplines={job.disciplines}, "
        f"location='{job.location}', "
        f"country='{metadata['country']}', "
        f"employment='{job.fulltime_parttime}', "
        f"education='{job.educational_background}', "
        f"description_len={len(job.description_text)}",
    )
    return job
