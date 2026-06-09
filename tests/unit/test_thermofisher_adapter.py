from __future__ import annotations

import json

from sources.thermofisher import adapter as thermofisher_adapter


def _page_html(*, hits: int, total_hits: int, jobs: list[dict[str, object]]) -> str:
    ddo = {
        "eagerLoadRefineSearch": {
            "hits": hits,
            "totalHits": total_hits,
            "data": {"jobs": jobs},
        }
    }
    return (
        "<script>"
        f"phApp.ddo = {json.dumps(ddo)}; "
        "phApp.experimentData = {};"
        "</script>"
    )


class _FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text

    def raise_for_status(self) -> None:
        return None


class _FakeSession:
    def __init__(self, pages: dict[str, str]) -> None:
        self._pages = pages
        self.requested_urls: list[str] = []

    def get(self, url: str, *, timeout: int) -> _FakeResponse:
        assert timeout == thermofisher_adapter.TIMEOUT_SECONDS
        self.requested_urls.append(url)
        return _FakeResponse(self._pages[url])


def test_parse_page_jobs_extracts_links_from_apply_urls() -> None:
    html = _page_html(
        hits=10,
        total_hits=60,
        jobs=[
            {
                "jobId": "R-0001",
                "title": "Sr Assembler",
                "applyUrl": (
                    "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                    "job/Eindhoven-Netherlands/Sr-Assembler_R-0001/apply"
                ),
            }
        ],
    )

    hits, total_hits, jobs = thermofisher_adapter.parse_page_jobs(html)

    assert hits == 10
    assert total_hits == 60
    assert jobs == [
        thermofisher_adapter.ThermoFisherListing(
            job_id="R-0001",
            title="Sr Assembler",
            job_url=(
                "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                "job/Eindhoven-Netherlands/Sr-Assembler_R-0001"
            ),
        )
    ]


def test_retrieve_thermofisher_job_links_deduplicates_ids_across_pages() -> None:
    first_page = _page_html(
        hits=2,
        total_hits=4,
        jobs=[
            {
                "jobId": "R-0001",
                "title": "Sr Assembler",
                "applyUrl": (
                    "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                    "job/Eindhoven-Netherlands/Sr-Assembler_R-0001/apply"
                ),
            },
            {
                "jobId": "R-0002",
                "title": "Operations Engineer",
                "applyUrl": (
                    "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                    "job/Eindhoven-Netherlands/Operations-Engineer_R-0002/apply"
                ),
            },
        ],
    )
    second_page = _page_html(
        hits=2,
        total_hits=4,
        jobs=[
            {
                "jobId": "R-0002",
                "title": "Operations Engineer",
                "applyUrl": (
                    "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                    "job/Eindhoven-Netherlands/Operations-Engineer_R-0002/apply"
                ),
            },
            {
                "jobId": "R-0003",
                "title": "Software Architect",
                "applyUrl": (
                    "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/"
                    "job/Eindhoven-Netherlands/Software-Architect_R-0003/apply"
                ),
            },
        ],
    )
    session = _FakeSession(
        {
            thermofisher_adapter.build_page_url(0): first_page,
            thermofisher_adapter.build_page_url(2): second_page,
        }
    )

    result = thermofisher_adapter.retrieve_thermofisher_job_links(
        None,
        session=session,
    )

    assert result.job_links == [
        "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/job/Eindhoven-Netherlands/Sr-Assembler_R-0001",
        "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/job/Eindhoven-Netherlands/Operations-Engineer_R-0002",
        "https://thermofisher.wd5.myworkdayjobs.com/ThermoFisherCareers/job/Eindhoven-Netherlands/Software-Architect_R-0003",
    ]
    assert result.validation_report["site_total_hits"] == 4
    assert result.validation_report["duplicate_job_ids"] == ["R-0002"]
    assert session.requested_urls == [
        thermofisher_adapter.build_page_url(0),
        thermofisher_adapter.build_page_url(2),
    ]
