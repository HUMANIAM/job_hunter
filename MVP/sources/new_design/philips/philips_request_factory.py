from __future__ import annotations

from typing import Any

from MVP.sources.new_design.retrieval_access import http_access as http
from MVP.sources.new_design.philips import philips_config as config


def build_listing_request(
    *,
    offset: int,
    country_facet_id: str | None,
) -> http.HttpRequest:
    headers = _build_headers()
    payload = _build_payload(
        offset=offset,
        country_facet_id=country_facet_id,
    )

    return http.HttpRequest(
        url=config.API_URL,
        headers=headers,
        body=payload,
        timeout_seconds=config.REQUEST_TIMEOUT_SECONDS,
    )


def _build_headers() -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Accept-Language": config.DEFAULT_LOCALE,
        "Content-Type": "application/json",
        "Origin": config.ORIGIN_URL,
        "Referer": _build_page_url(),
    }


def _build_payload(
    *,
    offset: int,
    country_facet_id: str | None,
) -> dict[str, Any]:
    applied_facets = (
        {config.LOCATION_FACET_ID: [country_facet_id]}
        if country_facet_id
        else {}
    )

    return {
        "appliedFacets": applied_facets,
        "limit": config.PHILIPS_PAGE_SIZE,
        "offset": offset,
        "searchText": "",
    }


def _build_page_url() -> str:
    return config.ENTRY_URL
