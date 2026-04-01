from __future__ import annotations

from dataclasses import dataclass

import fetch_jobs
from sources.base import SourceDefinition, SourceRetrievalResult


def test_parse_args_accepts_company_option() -> None:
    args = fetch_jobs.parse_args(["--company", "sioux"])

    assert args.company == "sioux"


def test_parse_args_defaults_to_sioux() -> None:
    args = fetch_jobs.parse_args([])

    assert args.company == "sioux"


@dataclass
class FakeJob:
    title: str | None
    description_text: str | None
    url: str


class FakeParser:
    def __init__(self) -> None:
        self.calls: list[tuple[object, str, list[str], object]] = []

    def fetch_job(
        self,
        page: object,
        url: str,
        disciplines: list[str] | None = None,
        log_message=None,
    ) -> FakeJob | None:
        self.calls.append((page, url, disciplines or [], log_message))
        if url.endswith("/skip"):
            return None
        return FakeJob(
            title="Controls Engineer",
            description_text="Build control software.",
            url=url,
        )


class FakeAdapter:
    def __init__(self, retrieval: SourceRetrievalResult) -> None:
        self.retrieval = retrieval
        self.logged_reports: list[dict[str, object]] = []

    def retrieve_job_links(self, browser: object) -> SourceRetrievalResult:
        return self.retrieval

    def log_validation_report(self, report: dict[str, object]) -> None:
        self.logged_reports.append(report)


class FakePage:
    pass


class FakeContext:
    def __init__(self) -> None:
        self.page = FakePage()
        self.closed = False

    def new_page(self) -> FakePage:
        return self.page

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self) -> None:
        self.context = FakeContext()

    def new_context(self) -> FakeContext:
        return self.context


def test_fetch_source_jobs_retrieves_validates_and_parses(monkeypatch) -> None:
    validation_report = {"facet_union_count": 2, "pagination_count": 2}
    retrieval = SourceRetrievalResult(
        job_links=[
            "https://example.com/jobs/controls",
            "https://example.com/jobs/skip",
        ],
        discipline_map={
            "https://example.com/jobs/controls": ["Control"],
        },
        validation_report=validation_report,
    )
    adapter = FakeAdapter(retrieval)
    parser = FakeParser()
    browser = FakeBrowser()
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=adapter,
        parser=parser,
    )
    messages: list[str] = []
    validation_writes: list[tuple[dict[str, object], str, object]] = []

    monkeypatch.setattr(fetch_jobs, "log", messages.append)
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_validation_report",
        lambda report, *, company_slug, log_message: validation_writes.append(
            (report, company_slug, log_message)
        ),
    )

    jobs = fetch_jobs.fetch_source_jobs(browser, source)

    assert jobs == [
        FakeJob(
            title="Controls Engineer",
            description_text="Build control software.",
            url="https://example.com/jobs/controls",
        )
    ]
    assert adapter.logged_reports == [validation_report]
    assert validation_writes == [
        (validation_report, "sioux", fetch_jobs.log)
    ]
    assert parser.calls == [
        (
            browser.context.page,
            "https://example.com/jobs/controls",
            ["Control"],
            fetch_jobs.log,
        ),
        (
            browser.context.page,
            "https://example.com/jobs/skip",
            [],
            fetch_jobs.log,
        ),
    ]
    assert browser.context.closed is True
    assert messages == [
        "fetch progress: [1/2]",
        "fetch progress: [2/2]",
        "closing browser after fetching 1 jobs",
    ]
