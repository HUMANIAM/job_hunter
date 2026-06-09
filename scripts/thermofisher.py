from __future__ import annotations

import json
import re
from dataclasses import dataclass

import requests

BASE_URL = "https://jobs.thermofisher.com/global/en/netherlands-jobs"
TIMEOUT_SECONDS = 30
DDO_PATTERN = re.compile(
    r"phApp\.ddo\s*=\s*(\{.*?\})\s*;\s*phApp\.experimentData\s*=",
    re.S,
)


@dataclass(frozen=True)
class JobListing:
    job_id: str
    title: str
    job_url: str


def build_page_url(offset: int) -> str:
    return BASE_URL if offset == 0 else f"{BASE_URL}?from={offset}&s=1"


def extract_search_payload(html: str) -> dict[str, object]:
    match = DDO_PATTERN.search(html)
    if match is None:
        raise RuntimeError("Could not find phApp.ddo search payload in page HTML.")

    payload = json.loads(match.group(1)).get("eagerLoadRefineSearch")
    if not isinstance(payload, dict):
        raise RuntimeError("Missing eagerLoadRefineSearch payload in page HTML.")

    return payload


def job_url_from_apply_url(apply_url: str) -> str:
    return apply_url[:-6] if apply_url.endswith("/apply") else apply_url


def parse_page_jobs(html: str) -> tuple[int, int, list[JobListing]]:
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

    jobs: list[JobListing] = []
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
            JobListing(
                job_id=job_id,
                title=title,
                job_url=job_url_from_apply_url(apply_url),
            )
        )

    return hits, total_hits, jobs


def collect_jobs(session: requests.Session | None = None) -> list[JobListing]:
    managed_session = session is None
    active_session = session or requests.Session()

    try:
        response = active_session.get(build_page_url(0), timeout=TIMEOUT_SECONDS)
        response.raise_for_status()
        hits, total_hits, first_page_jobs = parse_page_jobs(response.text)

        deduped_jobs: list[JobListing] = []
        seen_job_ids: set[str] = set()

        def add_jobs(page_jobs: list[JobListing]) -> None:
            for job in page_jobs:
                if job.job_id in seen_job_ids:
                    continue
                seen_job_ids.add(job.job_id)
                deduped_jobs.append(job)

        add_jobs(first_page_jobs)

        if hits <= 0:
            return deduped_jobs

        for offset in range(hits, total_hits, hits):
            response = active_session.get(build_page_url(offset), timeout=TIMEOUT_SECONDS)
            response.raise_for_status()
            _, _, page_jobs = parse_page_jobs(response.text)
            add_jobs(page_jobs)

        return deduped_jobs
    finally:
        if managed_session:
            active_session.close()


def main() -> int:
    for job in collect_jobs():
        print(f"{job.title} | {job.job_url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
