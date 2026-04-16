from __future__ import annotations

from urllib.parse import quote

import pytest
import requests

from clients.sources.api_listing_adapter import APIPageResult
from clients.sources.canon import adapter as canon_adapter_module
from clients.sources.canon.adapter import (
    API_URL,
    REQUEST_TIMEOUT_SECONDS,
    CanonAPIListingAdapter,
    CanonListingFilters,
    CanonPageState,
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


def test_build_page_url_uses_configured_filters() -> None:
    filters = CanonListingFilters(
        locale="nl_NL",
        location="Amsterdam",
        job_type="Internship",
        options_facets_job_type="Internship",
    )
    adapter = CanonAPIListingAdapter(filters=filters)

    page_url = adapter._build_page_url(3)

    expected_filters = quote(
        '{"jobType":["Internship"],"sfstd_jobLocation_obj":["Amsterdam"]}'
    )
    assert page_url == (
        "https://jobs.cpp.canon/search/"
        "?locale=nl_NL"
        "&optionsFacetsDD_customfield3=Internship"
        "&searchResultView=LIST"
        "&markerViewed="
        "&carouselIndex="
        "&pageNumber=3"
        f"&facetFilters={expected_filters}"
    )


def test_fetch_listing_response_posts_expected_payload() -> None:
    fake_response = FakeResponse(payload={"jobSearchResult": [], "totalJobs": 0})
    session = FakeSession(fake_response)
    adapter = CanonAPIListingAdapter(session=session)

    response = adapter._fetch_listing_response(CanonPageState(page_number=2))

    assert response == {"jobSearchResult": [], "totalJobs": 0}
    assert session.calls == [
        (
            API_URL,
            {
                "Content-Type": "application/json",
                "Referer": adapter._build_page_url(2),
            },
            {
                "locale": "en_GB",
                "pageNumber": 2,
                "sortBy": "",
                "keywords": "",
                "location": "",
                "facetFilters": {
                    "jobType": ["Professional"],
                    "sfstd_jobLocation_obj": ["Venlo"],
                },
                "brand": "",
                "skills": [],
                "categoryId": 0,
                "alertId": "",
                "rcmCandidateId": "",
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
            url=f"{API_URL}?page=4",
            raise_error=requests.HTTPError("boom"),
        )
    )
    adapter = CanonAPIListingAdapter(session=session)
    monkeypatch.setattr(canon_adapter_module, "log", messages.append)

    with pytest.raises(requests.HTTPError):
        adapter._fetch_listing_response(CanonPageState(page_number=4))

    assert messages == [
        (
            "CanonAPIListingAdapter: request failed "
            "status=500 page=4 "
            f"url={API_URL}?page=4"
        )
    ]


def test_parse_listing_response_returns_expected_page_result() -> None:
    adapter = CanonAPIListingAdapter()

    page_result = adapter._parse_listing_response(
        {
            "totalJobs": 7,
            "jobSearchResult": [
                {
                    "response": {
                        "urlTitle": "systems-engineer",
                        "id": "12345",
                    }
                },
                {
                    "response": {
                        "unifiedUrlTitle": "software-architect",
                        "id": "67890",
                    }
                },
            ],
        },
        request_state=CanonPageState(page_number=1),
        page_index=2,
        remaining_job_budget=2,
    )

    assert page_result == APIPageResult(
        job_links={
            "https://jobs.cpp.canon/job/systems-engineer/12345-en_GB",
            "https://jobs.cpp.canon/job/software-architect/67890-en_GB",
        },
        next_request_state=CanonPageState(page_number=2),
        expected_total=7,
        is_last_page=False,
    )


def test_extract_job_urls_respects_limit_and_skips_incomplete_items() -> None:
    adapter = CanonAPIListingAdapter()

    urls = adapter._extract_job_urls(
        response_body={
            "jobSearchResult": [
                {"response": {"urlTitle": "systems-engineer", "id": "12345"}},
                {"response": {"unifiedUrlTitle": "software-architect", "id": "67890"}},
                {"response": {"urlTitle": "ignored-missing-id"}},
            ]
        },
        limit=1,
    )

    assert urls == {
        "https://jobs.cpp.canon/job/systems-engineer/12345-en_GB",
    }


def test_collect_job_links_retries_until_collection_is_complete(monkeypatch) -> None:
    adapter = CanonAPIListingAdapter(max_attempts=3)
    calls: list[int] = []
    attempts = iter(
        [
            ({"https://jobs.cpp.canon/job/a/1-en_GB"}, 3),
            (
                {
                    "https://jobs.cpp.canon/job/c/3-en_GB",
                    "https://jobs.cpp.canon/job/a/1-en_GB",
                    "https://jobs.cpp.canon/job/b/2-en_GB",
                },
                3,
            ),
        ]
    )

    def fake_collect_job_links_once(*, job_limit: int) -> tuple[set[str], int | None]:
        calls.append(job_limit)
        return next(attempts)

    monkeypatch.setattr(adapter, "_collect_job_links_once", fake_collect_job_links_once)

    links = adapter.collect_job_links(job_limit=5)

    assert links == [
        "https://jobs.cpp.canon/job/a/1-en_GB",
        "https://jobs.cpp.canon/job/b/2-en_GB",
        "https://jobs.cpp.canon/job/c/3-en_GB",
    ]
    assert calls == [5, 5]
