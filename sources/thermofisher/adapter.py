from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any

import requests

from infra.logging import log

START_URL = "https://jobs.thermofisher.com/global/en/netherlands-jobs"
TARGET_COUNTRIES = ("Netherlands",)
TARGET_LANGUAGES: tuple[str, ...] = ()
TIMEOUT_SECONDS = 30
DDO_PATTERN = re.compile(
    r"phApp\.ddo\s*=\s*(\{.*?\})\s*;\s*phApp\.experimentData\s*=",
    re.S,
)


@dataclass(frozen=True)
class ThermoFisherListing:
    job_id: str
    title: str
    job_url: str


@dataclass
class ThermoFisherRetrievalResult:
    job_links: list[str]
    discipline_map: dict[str, list[str]]
    validation_report: dict[str, object]


def build_page_url(offset: int) -> str:
    return START_URL if offset == 0 else f"{START_URL}?from={offset}&s=1"


def job_url_from_apply_url(apply_url: str) -> str:
    return apply_url[:-6] if apply_url.endswith("/apply") else apply_url


def extract_search_payload(html: str) -> dict[str, object]:
    match = DDO_PATTERN.search(html)
    if match is None:
        raise RuntimeError("Could not find phApp.ddo search payload in page HTML.")

    payload = json.loads(match.group(1)).get("eagerLoadRefineSearch")
    if not isinstance(payload, dict):
        raise RuntimeError("Missing eagerLoadRefineSearch payload in page HTML.")

    return payload


def parse_page_jobs(html: str) -> tuple[int, int, list[ThermoFisherListing]]:
    payload = extract_search_payload(html)
    hits = payload.get("hits")
    total_hits = payload.get("totalHits")
    data = payload.get("data")
    if not isinstance(hits, int) or not isinstance(total_hits, int):
        raise RuntimeError("Search payload is missing numeric hits/totalHits values.")
    if not isinstance(data, dict):
        raise RuntimeError("Search payload is missing the data container.")

    raw_jobs = data.get("jobs")
    if not isinstance(raw_jobs, list):
        raise RuntimeError("Search payload is missing the jobs list.")

    jobs: list[ThermoFisherListing] = []
    for raw_job in raw_jobs:
        if not isinstance(raw_job, dict):
            raise RuntimeError("Encountered a non-dictionary job row in payload.")

        job_id = raw_job.get("jobId")
        title = raw_job.get("title")
        apply_url = raw_job.get("applyUrl")
        if not isinstance(job_id, str) or not isinstance(title, str):
            raise RuntimeError("Encountered a job row without jobId/title.")
        if not isinstance(apply_url, str):
            raise RuntimeError(f"Encountered a job row without applyUrl for {job_id}.")

        jobs.append(
            ThermoFisherListing(
                job_id=job_id,
                title=title,
                job_url=job_url_from_apply_url(apply_url),
            )
        )

    return hits, total_hits, jobs


def build_collection_validation_report(
    *,
    first_page_hits: int,
    total_hits: int,
    row_job_ids: list[str],
    returned_jobs: list[ThermoFisherListing],
    collected_unique_count: int,
    job_limit: int | None,
) -> dict[str, object]:
    seen_counts: dict[str, int] = {}
    duplicate_job_ids: list[str] = []
    for job_id in row_job_ids:
        seen_counts[job_id] = seen_counts.get(job_id, 0) + 1
        if seen_counts[job_id] == 2:
            duplicate_job_ids.append(job_id)

    return {
        "fetched_at_unix": int(time.time()),
        "source": START_URL,
        "configured_countries": list(TARGET_COUNTRIES),
        "configured_languages": list(TARGET_LANGUAGES),
        "first_page_hits": first_page_hits,
        "site_total_hits": total_hits,
        "row_count_collected": len(row_job_ids),
        "unique_job_count": collected_unique_count,
        "returned_job_count": len(returned_jobs),
        "job_limit": job_limit,
        "duplicate_job_ids": duplicate_job_ids,
        "duplicate_row_count": len(row_job_ids) - collected_unique_count,
        "job_links": [job.job_url for job in returned_jobs],
    }


def log_collection_validation_report(report: dict[str, object]) -> None:
    log("collection validation report")
    log(f"site_total_hits={report['site_total_hits']}")
    log(f"row_count_collected={report['row_count_collected']}")
    log(f"unique_job_count={report['unique_job_count']}")
    log(f"duplicate_row_count={report['duplicate_row_count']}")
    for job_id in report["duplicate_job_ids"]:
        log(f"duplicate_job_id: {job_id}")


def retrieve_thermofisher_job_links(
    _browser: Any,
    *,
    job_limit: int | None = None,
    session: requests.Session | None = None,
) -> ThermoFisherRetrievalResult:
    managed_session = session is None
    active_session = session or requests.Session()

    try:
        deduped_jobs: list[ThermoFisherListing] = []
        seen_job_ids: set[str] = set()
        row_job_ids: list[str] = []

        response = active_session.get(build_page_url(0), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        hits, total_hits, first_page_jobs = parse_page_jobs(response.text)

        def add_jobs(page_jobs: list[ThermoFisherListing]) -> None:
            for job in page_jobs:
                row_job_ids.append(job.job_id)
                if job.job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job.job_id)
                deduped_jobs.append(job)

        add_jobs(first_page_jobs)
        log(
            "thermofisher page 1: "
            f"rows={len(first_page_jobs)} | cumulative_unique={len(deduped_jobs)}"
        )

        if hits > 0:
            page_index = 2
            for offset in range(hits, total_hits, hits):
                if job_limit is not None and len(deduped_jobs) >= job_limit:
                    log("thermofisher: reached job limit, stopping pagination")
                    break

                response = active_session.get(
                    build_page_url(offset),
                    timeout=TIMEOUT_SECONDS,
                )
                response.raise_for_status()
                _, _, page_jobs = parse_page_jobs(response.text)
                add_jobs(page_jobs)
                log(
                    f"thermofisher page {page_index}: "
                    f"rows={len(page_jobs)} | cumulative_unique={len(deduped_jobs)}"
                )
                page_index += 1

        if job_limit is not None:
            deduped_jobs = deduped_jobs[:job_limit]

        validation_report = build_collection_validation_report(
            first_page_hits=hits,
            total_hits=total_hits,
            row_job_ids=row_job_ids,
            returned_jobs=deduped_jobs,
            collected_unique_count=len(seen_job_ids),
            job_limit=job_limit,
        )

        return ThermoFisherRetrievalResult(
            job_links=[job.job_url for job in deduped_jobs],
            discipline_map={},
            validation_report=validation_report,
        )
    finally:
        if managed_session:
            active_session.close()
