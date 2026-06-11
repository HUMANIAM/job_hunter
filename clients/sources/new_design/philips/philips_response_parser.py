from __future__ import annotations

from typing import Any

from clients.sources.new_design.types import VacancyLinks
from clients.sources.new_design.philips import philips_config as config


def discover_country_facet_id(
    response_content: dict[str, Any],
    *,
    country: str,
) -> str | None:
    facets = response_content.get("facets") or []

    for facet in facets:
        if facet.get("facetParameter") != config.LOCATION_GROUP_FACET_ID:
            continue

        for group in facet.get("values") or []:
            if group.get("facetParameter") != config.LOCATION_FACET_ID:
                continue

            for value in group.get("values") or []:
                descriptor = value.get("descriptor")
                if not isinstance(descriptor, str):
                    continue

                if descriptor.strip() != country:
                    continue

                facet_id = value.get("id")
                if facet_id:
                    return str(facet_id)

    return None


def get_job_postings(response_content: dict[str, Any]) -> list[dict[str, Any]]:
    job_postings = response_content.get("jobPostings") or []
    return [
        job_posting
        for job_posting in job_postings
        if isinstance(job_posting, dict)
    ]


def extract_vacancy_links(
    job_postings: list[dict[str, Any]],
    *,
    links_limit: int | None,
) -> VacancyLinks:
    links: set[str] = set()

    if links_limit is not None and links_limit <= 0:
        return VacancyLinks(links=links)

    for job_posting in job_postings:
        external_path = job_posting.get("externalPath")
        if not isinstance(external_path, str):
            continue

        if not external_path.startswith(config.JOB_PATH_PREFIX):
            continue

        links.add(_build_job_url(external_path))
        if links_limit is not None and len(links) >= links_limit:
            break

    return VacancyLinks(links=links)


def _build_job_url(external_path: str) -> str:
    normalized_path = (
        external_path if external_path.startswith("/") else f"/{external_path}"
    )
    return f"{config.ENTRY_URL}{normalized_path}"
