from __future__ import annotations

import json
import re
from typing import Any, List
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from clients.base import BaseClientAdapter
from infra.browser import open_and_prepare_page
from infra.logging import log


PHILIPS_ENTRY_URL = "https://philips.wd3.myworkdayjobs.com/nl-nl/jobs-and-careers"
PHILIPS_JOBS_API_URL = (
    "https://philips.wd3.myworkdayjobs.com/wday/cxs/philips/jobs-and-careers/jobs"
)
PHILIPS_API_LOCALE = "nl-NL"
PHILIPS_PAGE_SIZE = 20
PHILIPS_NETHERLANDS_COUNTRY_RE = re.compile(
    r'"addressCountry"\s*:\s*"(?:Nederland|Netherlands|NL)"',
    re.IGNORECASE,
)

PHILIPS_JOB_URL_RE = re.compile(
    r"^https://philips\.wd3\.myworkdayjobs\.com/"
    r"(?:[a-z]{2}(?:-[a-z]{2})?/)?jobs-and-careers/job/[^?#]+$",
    re.IGNORECASE,
)


class PhilipsClientAdapter(BaseClientAdapter):
    ENTRY_URL = PHILIPS_ENTRY_URL

    def _collect_job_links_in_context(
        self,
        context: Any,
        page: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        self._open_page(page, self.ENTRY_URL)
        hrefs = self._collect_links_from_paginated_listing(
            page,
            context="philips nl listing",
            job_limit=job_limit,
        )

        log(f"philips nl listing: collected {len(hrefs)} unique job links")
        return sorted(hrefs)

    def _open_page(self, page: Any, url: str) -> None:
        open_and_prepare_page(
            page,
            url,
            wait_for=["a[data-automation-id='jobTitle'][href]"],
        )
        log(f"current page url: {page.url}")

    def _is_job_url(self, url: str) -> bool:
        return bool(PHILIPS_JOB_URL_RE.match(url))

    def _build_job_url(self, external_path: str) -> str:
        return urljoin(self.ENTRY_URL.rstrip("/") + "/", external_path.lstrip("/"))

    def _is_netherlands_job_page(self, url: str) -> bool:
        try:
            with urlopen(url, timeout=30) as response:
                html = response.read().decode("utf-8", errors="ignore")
        except Exception:
            return False

        return bool(PHILIPS_NETHERLANDS_COUNTRY_RE.search(html))

    def _fetch_job_results(
        self,
        *,
        applied_facets: dict[str, list[str]] | None = None,
        limit: int,
        offset: int,
        search_text: str = "",
    ) -> dict[str, Any]:
        payload = {
            "appliedFacets": applied_facets or {},
            "limit": limit,
            "offset": offset,
            "searchText": search_text,
        }
        request = Request(
            PHILIPS_JOBS_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Accept-Language": PHILIPS_API_LOCALE,
                "Content-Type": "application/json",
                "Origin": "https://philips.wd3.myworkdayjobs.com",
                "Referer": self.ENTRY_URL,
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data if isinstance(data, dict) else {}

    def _discover_netherlands_facet_id(self) -> str | None:
        results = self._fetch_job_results(limit=1, offset=0)
        facets = results.get("facets") or []

        for facet in facets:
            if facet.get("facetParameter") != "locationMainGroup":
                continue

            for group in facet.get("values") or []:
                if group.get("facetParameter") != "locationHierarchy1":
                    continue

                for value in group.get("values") or []:
                    descriptor = str(value.get("descriptor") or "").strip()
                    if descriptor == "Netherlands":
                        facet_id = value.get("id")
                        if facet_id:
                            return str(facet_id)

        return None

    def _collect_job_links_from_page(
        self,
        results: dict[str, Any],
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        hrefs: set[str] = set()
        jobs = results.get("jobPostings") or []
        log(f"{context}: found {len(jobs)} job postings")

        for job in jobs:
            external_path = job.get("externalPath")
            if not external_path:
                continue

            full_url = self._build_job_url(str(external_path))
            if not self._is_job_url(full_url):
                continue

            if not self._is_netherlands_job_page(full_url):
                log(f"{context}: skipped non-NL job {full_url}")
                continue

            hrefs.add(full_url)
            if len(hrefs) >= job_limit:
                break

        log(f"{context}: collected {len(hrefs)} job links from current page")
        return hrefs

    def _collect_links_from_paginated_listing(
        self,
        page: Any,
        context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        collected_links: set[str] = set()
        page_index = 1
        offset = 0

        facet_id = self._discover_netherlands_facet_id()
        if not facet_id:
            log(f"{context}: Netherlands facet not found")
            return collected_links

        while True:
            requested_limit = min(PHILIPS_PAGE_SIZE, job_limit - len(collected_links))
            results = self._fetch_job_results(
                applied_facets={"locationHierarchy1": [facet_id]},
                limit=requested_limit,
                offset=offset,
            )

            job_postings = results.get("jobPostings") or []
            if not job_postings:
                log(f"{context}: no results for offset {offset}")
                break

            page_links = self._collect_job_links_from_page(
                results,
                f"{context} page {page_index}",
                job_limit=job_limit - len(collected_links),
            )

            before = len(collected_links)
            collected_links.update(page_links)
            after = len(collected_links)

            log(
                f"{context} page {page_index}: "
                f"added {after - before} new links | cumulative={after}"
            )

            if len(collected_links) >= job_limit:
                log(f"{context}: reached job limit, stopping")
                break

            offset += len(job_postings)
            page_index += 1

            if len(job_postings) < requested_limit:
                log(f"{context}: reached final results page")
                break

        return collected_links
