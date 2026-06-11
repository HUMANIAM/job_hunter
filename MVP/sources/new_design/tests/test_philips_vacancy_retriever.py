from __future__ import annotations

from MVP.sources.new_design.retrieval_access import http_access as http
from MVP.sources.new_design import vacancy_retriever as vr
from MVP.sources.new_design.philips import philips_config as config
from MVP.sources.new_design.philips.philips_vacancy_retriever import (
    PhilipsPageCursor,
    PhilipsVacancyRetriever,
)
from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks


class FakeHttpAccess(http.HttpAccess):
    def __init__(self, responses: list[http.HttpResponse]) -> None:
        self._responses = responses
        self.requests: list[http.HttpRequest] = []

    def post(self, request: http.HttpRequest) -> http.HttpResponse:
        self.requests.append(request)
        return self._responses.pop(0)

    def get(self, request: http.HttpRequest) -> http.HttpResponse:
        self.requests.append(request)
        return self._responses.pop(0)


def test_retrieve_vacancy_page_gets_html_page() -> None:
    http_access = FakeHttpAccess(
        [
            http.HttpResponse(
                status_code=200,
                content="<html>Philips vacancy</html>",
            )
        ]
    )
    retriever = PhilipsVacancyRetriever(http_access=http_access)

    page = retriever.retrieve_vacancy_page("https://example.test/job/1")

    assert page == "<html>Philips vacancy</html>"
    assert http_access.requests == [
        http.HttpRequest(
            url="https://example.test/job/1",
            headers={
                "Accept": "text/html",
                "Accept-Language": config.DEFAULT_LOCALE,
            },
            body={},
            timeout_seconds=config.REQUEST_TIMEOUT_SECONDS,
        )
    ]


def test_get_initial_cursor_discovers_country_facet_id() -> None:
    http_access = FakeHttpAccess(
        [
            http.HttpResponse(
                status_code=200,
                content={
                    "facets": [
                        {
                            "facetParameter": "locationMainGroup",
                            "values": [
                                {
                                    "facetParameter": "locationHierarchy1",
                                    "values": [
                                        {
                                            "descriptor": "Netherlands",
                                            "id": "facet-123",
                                        },
                                    ],
                                },
                            ],
                        },
                    ],
                },
            ),
        ]
    )
    retriever = PhilipsVacancyRetriever(http_access=http_access)

    cursor = retriever._get_initial_cursor(
        criteria=VacancyLinkRetrievalCriteria(country="Netherlands")
    )

    assert cursor == PhilipsPageCursor(offset=0, country_facet_id="facet-123")
    assert http_access.requests[0].body == {
        "appliedFacets": {},
        "limit": config.PHILIPS_PAGE_SIZE,
        "offset": 0,
        "searchText": "",
    }


def test_retrieve_listing_batch_advances_cursor_when_batch_is_full() -> None:
    job_postings = [
        {"externalPath": f"/job/Eindhoven/Role_{index}"}
        for index in range(config.PHILIPS_PAGE_SIZE)
    ]
    http_access = FakeHttpAccess(
        [http.HttpResponse(status_code=200, content={"jobPostings": job_postings})]
    )
    retriever = PhilipsVacancyRetriever(http_access=http_access)
    progress = vr.VacancyLinkRetrievalProgress(
        retrieved_links=VacancyLinks(links=set()),
        criteria=VacancyLinkRetrievalCriteria(),
        iteration_index=0,
    )

    batch = retriever._retrieve_listing_batch(
        cursor=PhilipsPageCursor(offset=20, country_facet_id="facet-123"),
        retrieval_progress=progress,
    )

    assert batch.next_cursor == PhilipsPageCursor(
        offset=40,
        country_facet_id="facet-123",
    )
    assert f"{config.ENTRY_URL}/job/Eindhoven/Role_0" in batch.retrieved_links.links
    assert http_access.requests[0].body["appliedFacets"] == {
        "locationHierarchy1": ["facet-123"],
    }
    assert http_access.requests[0].body["offset"] == 20


def test_retrieve_listing_batch_completes_when_batch_is_partial() -> None:
    http_access = FakeHttpAccess(
        [
            http.HttpResponse(
                status_code=200,
                content={"jobPostings": [{"externalPath": "/job/Eindhoven/Role_1"}]},
            )
        ]
    )
    retriever = PhilipsVacancyRetriever(http_access=http_access)
    progress = vr.VacancyLinkRetrievalProgress(
        retrieved_links=VacancyLinks(links=set()),
        criteria=VacancyLinkRetrievalCriteria(),
        iteration_index=0,
    )

    batch = retriever._retrieve_listing_batch(
        cursor=PhilipsPageCursor(offset=40, country_facet_id="facet-123"),
        retrieval_progress=progress,
    )

    assert batch.next_cursor is None
    assert batch.retrieved_links == VacancyLinks(
        links={f"{config.ENTRY_URL}/job/Eindhoven/Role_1"}
    )
