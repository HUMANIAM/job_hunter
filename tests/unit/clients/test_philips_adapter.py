from __future__ import annotations

import pytest
import requests

from clients.sources.api_listing_adapter import APIPageResult
from clients.sources.philips import adapter as philips_adapter_module
from clients.sources.philips.adapter import (
    API_URL,
    DEFAULT_MAX_ATTEMPTS,
    ENTRY_URL,
    PHILIPS_PAGE_SIZE,
    REQUEST_TIMEOUT_SECONDS,
    PhilipsAPIListingAdapter,
    PhilipsListingFilters,
    PhilipsPageState,
)


class FakeResponse:
    def __init__(
        self,
        *,
        payload: dict,
        status_code: int = 200,
        url: str = API_URL,
        raise_error: Exception | None = None,
    ) -> None:
        self._payload = payload
        self.status_code = status_code
        self.url = url
        self._raise_error = raise_error

    def raise_for_status(self) -> None:
        if self._raise_error is not None:
            raise self._raise_error

    def json(self) -> dict:
        return self._payload


class FakeSession:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str], dict, int]] = []

    def post(
        self,
        url: str,
        *,
        headers: dict[str, str],
        json: dict,
        timeout: int,
    ) -> FakeResponse:
        self.calls.append((url, headers, json, timeout))
        return self.response


def test_build_job_url_preserves_jobs_listing_prefix() -> None:
    adapter = PhilipsAPIListingAdapter()

    job_url = adapter._build_job_url("/job/Eindhoven/Internship_572430")

    assert job_url == (
        "https://philips.wd3.myworkdayjobs.com/"
        "nl-nl/jobs-and-careers/job/Eindhoven/Internship_572430"
    )


def test_fetch_listing_response_posts_expected_payload() -> None:
    fake_response = FakeResponse(payload={"jobPostings": [], "total": 0})
    session = FakeSession(fake_response)
    adapter = PhilipsAPIListingAdapter(session=session)

    response = adapter._fetch_listing_response(
        PhilipsPageState(offset=40, country_facet_id="facet-123"),
    )

    assert response == {"jobPostings": [], "total": 0}
    assert session.calls == [
        (
            API_URL,
            {
                "Accept": "application/json",
                "Accept-Language": "nl-NL",
                "Content-Type": "application/json",
                "Origin": "https://philips.wd3.myworkdayjobs.com",
                "Referer": ENTRY_URL,
            },
            {
                "appliedFacets": {"locationHierarchy1": ["facet-123"]},
                "limit": PHILIPS_PAGE_SIZE,
                "offset": 40,
                "searchText": "",
            },
            REQUEST_TIMEOUT_SECONDS,
        )
    ]


def test_fetch_listing_response_logs_and_reraises_http_error(monkeypatch) -> None:
    messages: list[str] = []
    session = FakeSession(
        FakeResponse(
            payload={},
            status_code=500,
            url=f"{API_URL}?offset=20",
            raise_error=requests.HTTPError("boom"),
        )
    )
    adapter = PhilipsAPIListingAdapter(session=session)
    monkeypatch.setattr(philips_adapter_module, "log", messages.append)

    with pytest.raises(requests.HTTPError):
        adapter._fetch_listing_response(
            PhilipsPageState(offset=20, country_facet_id="facet-123"),
        )

    assert messages == [
        (
            "PhilipsAPIListingAdapter: request failed "
            "status=500 offset=20 "
            f"url={API_URL}?offset=20"
        )
    ]


def test_discover_country_facet_id_uses_configured_filters() -> None:
    fake_response = FakeResponse(
        payload={
            "facets": [
                {
                    "facetParameter": "locationMainGroup",
                    "values": [
                        {
                            "facetParameter": "locationHierarchy1",
                            "values": [
                                {"descriptor": "Nederland", "id": "facet-123"},
                            ],
                        }
                    ],
                }
            ]
        }
    )
    session = FakeSession(fake_response)
    adapter = PhilipsAPIListingAdapter(
        session=session,
        filters=PhilipsListingFilters(country_descriptor="Nederland"),
    )

    facet_id = adapter._discover_country_facet_id()

    assert facet_id == "facet-123"
    assert session.calls == [
        (
            API_URL,
            {
                "Accept": "application/json",
                "Accept-Language": "nl-NL",
                "Content-Type": "application/json",
                "Origin": "https://philips.wd3.myworkdayjobs.com",
                "Referer": ENTRY_URL,
            },
            {
                "appliedFacets": {},
                "limit": PHILIPS_PAGE_SIZE,
                "offset": 0,
                "searchText": "",
            },
            REQUEST_TIMEOUT_SECONDS,
        )
    ]


def test_parse_listing_response_returns_expected_page_result() -> None:
    adapter = PhilipsAPIListingAdapter()
    job_postings = [
        {"externalPath": f"/job/Eindhoven/Role_{index}"}
        for index in range(PHILIPS_PAGE_SIZE - 1)
    ]
    job_postings.append({"externalPath": "/not-a-job"})

    page_result = adapter._parse_listing_response(
        {
            "total": 45,
            "jobPostings": job_postings,
        },
        request_state=PhilipsPageState(offset=20, country_facet_id="facet-123"),
        page_index=2,
        remaining_job_budget=2,
    )

    assert page_result == APIPageResult(
        job_links={
            f"{ENTRY_URL}/job/Eindhoven/Role_0",
            f"{ENTRY_URL}/job/Eindhoven/Role_1",
        },
        next_request_state=PhilipsPageState(offset=40, country_facet_id="facet-123"),
        expected_total=45,
        is_last_page=False,
    )


def test_extract_job_urls_respects_limit_after_filtering() -> None:
    adapter = PhilipsAPIListingAdapter()

    filtered_job_postings = adapter._filter_job_postings(
        job_postings=[
            {"externalPath": "/job/Eindhoven/Internship_572430"},
            {"externalPath": "/job/Amsterdam/Junior_581280"},
            {"externalPath": "/not-a-job"},
            {"externalPath": None},
        ]
    )
    urls = adapter._extract_job_urls(
        job_postings=filtered_job_postings,
        limit=1,
    )

    assert urls == {
        f"{ENTRY_URL}/job/Eindhoven/Internship_572430",
    }


def test_collect_job_links_uses_single_attempt_by_default(monkeypatch) -> None:
    adapter = PhilipsAPIListingAdapter()
    calls: list[int] = []

    def fake_collect_job_links_once(*, job_limit: int) -> tuple[set[str], int | None]:
        calls.append(job_limit)
        return ({f"{ENTRY_URL}/job/Eindhoven/Internship_572430"}, 1)

    monkeypatch.setattr(adapter, "_collect_job_links_once", fake_collect_job_links_once)

    links = adapter.collect_job_links(job_limit=5)

    assert links == [f"{ENTRY_URL}/job/Eindhoven/Internship_572430"]
    assert calls == [5]
    assert adapter._get_max_attempts() == DEFAULT_MAX_ATTEMPTS
