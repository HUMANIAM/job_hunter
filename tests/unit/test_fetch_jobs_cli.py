from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from types import ModuleType, SimpleNamespace
import sys

if "playwright.sync_api" not in sys.modules:
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: None
    sync_api.Browser = object
    sync_api.Page = object
    sync_api.Playwright = object
    sync_api.TimeoutError = TimeoutError

    playwright = ModuleType("playwright")
    playwright.sync_api = sync_api

    sys.modules["playwright"] = playwright
    sys.modules["playwright.sync_api"] = sync_api

import fetch_jobs
from sources.base import SourceDefinition, SourceRetrievalResult


def test_parse_args_accepts_company_option() -> None:
    args = fetch_jobs.parse_args(["--company", "sioux"])

    assert args.company == "sioux"


def test_parse_args_defaults_to_final_output_only() -> None:
    args = fetch_jobs.parse_args([])

    assert args.company == "sioux"
    assert args.write_raw is False
    assert args.write_evaluated is False
    assert args.write_validation is False


def test_parse_args_accepts_optional_output_flags() -> None:
    args = fetch_jobs.parse_args(
        [
            "--company",
            "sioux",
            "--write-raw",
            "--write-evaluated",
            "--write-validation",
        ]
    )

    assert args.company == "sioux"
    assert args.write_raw is True
    assert args.write_evaluated is True
    assert args.write_validation is True


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


def test_fetch_source_jobs_skips_validation_file_by_default(monkeypatch) -> None:
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
    assert validation_writes == []
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


def test_fetch_source_jobs_writes_validation_when_enabled(monkeypatch) -> None:
    validation_report = {"facet_union_count": 2, "pagination_count": 2}
    retrieval = SourceRetrievalResult(
        job_links=[],
        discipline_map={},
        validation_report=validation_report,
    )
    adapter = FakeAdapter(retrieval)
    browser = FakeBrowser()
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=adapter,
        parser=FakeParser(),
    )
    validation_writes: list[tuple[dict[str, object], str, object]] = []

    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_validation_report",
        lambda report, *, company_slug, log_message: validation_writes.append(
            (report, company_slug, log_message)
        ),
    )

    fetch_jobs.fetch_source_jobs(
        browser,
        source,
        write_validation_report=True,
    )

    assert adapter.logged_reports == [validation_report]
    assert validation_writes == [
        (validation_report, "sioux", fetch_jobs.log)
    ]


@contextmanager
def _yield(value: object):
    yield value


def test_main_writes_only_kept_jobs_by_default(monkeypatch) -> None:
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=FakeAdapter(
            SourceRetrievalResult(
                job_links=[],
                discipline_map={},
                validation_report={},
            )
        ),
        parser=FakeParser(),
    )
    fetched_jobs = [
        FakeJob(
            title="Controls Engineer",
            description_text="Build control software.",
            url="https://example.com/jobs/controls",
        )
    ]
    kept_writes: list[dict[str, object]] = []
    raw_calls: list[dict[str, object]] = []
    evaluated_calls: list[dict[str, object]] = []
    fetch_calls: list[bool] = []

    monkeypatch.setattr(fetch_jobs, "get_source", lambda company: source)
    monkeypatch.setattr(
        fetch_jobs,
        "fetch_source_jobs",
        lambda browser, resolved_source, *, write_validation_report=False: (
            fetch_calls.append(write_validation_report) or fetched_jobs
        ),
    )
    monkeypatch.setattr(
        fetch_jobs,
        "evaluate_jobs",
        lambda jobs, *, log_message=None: SimpleNamespace(
            evaluated_jobs=[{"title": "Controls Engineer", "decision": "keep"}],
            kept_jobs=jobs,
        ),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_raw_jobs",
        lambda **kwargs: raw_calls.append(kwargs),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_evaluated_jobs",
        lambda **kwargs: evaluated_calls.append(kwargs),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_kept_jobs",
        lambda **kwargs: kept_writes.append(kwargs),
    )
    monkeypatch.setattr(fetch_jobs, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        fetch_jobs,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(fetch_jobs, "log", lambda _message: None)

    fetch_jobs.main([])

    assert fetch_calls == [False]
    assert raw_calls == []
    assert evaluated_calls == []
    assert len(kept_writes) == 1
    assert kept_writes[0]["jobs"] == [
        {
            "title": "Controls Engineer",
            "description_text": "Build control software.",
            "url": "https://example.com/jobs/controls",
        }
    ]
    assert kept_writes[0]["total_jobs"] == 1
    assert kept_writes[0]["company_slug"] == "sioux"


def test_main_writes_optional_outputs_when_requested(monkeypatch) -> None:
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=FakeAdapter(
            SourceRetrievalResult(
                job_links=[],
                discipline_map={},
                validation_report={},
            )
        ),
        parser=FakeParser(),
    )
    fetched_jobs = [
        FakeJob(
            title="Controls Engineer",
            description_text="Build control software.",
            url="https://example.com/jobs/controls",
        )
    ]
    raw_calls: list[dict[str, object]] = []
    evaluated_calls: list[dict[str, object]] = []
    kept_calls: list[dict[str, object]] = []
    fetch_calls: list[bool] = []

    monkeypatch.setattr(fetch_jobs, "get_source", lambda company: source)
    monkeypatch.setattr(
        fetch_jobs,
        "fetch_source_jobs",
        lambda browser, resolved_source, *, write_validation_report=False: (
            fetch_calls.append(write_validation_report) or fetched_jobs
        ),
    )
    monkeypatch.setattr(
        fetch_jobs,
        "evaluate_jobs",
        lambda jobs, *, log_message=None: SimpleNamespace(
            evaluated_jobs=[{"title": "Controls Engineer", "decision": "keep"}],
            kept_jobs=jobs,
        ),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_raw_jobs",
        lambda **kwargs: raw_calls.append(kwargs),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_evaluated_jobs",
        lambda **kwargs: evaluated_calls.append(kwargs),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_kept_jobs",
        lambda **kwargs: kept_calls.append(kwargs),
    )
    monkeypatch.setattr(fetch_jobs, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        fetch_jobs,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(fetch_jobs, "log", lambda _message: None)

    fetch_jobs.main(
        [
            "--write-raw",
            "--write-evaluated",
            "--write-validation",
        ]
    )

    assert fetch_calls == [True]
    assert len(raw_calls) == 1
    assert raw_calls[0]["jobs"] == [
        {
            "title": "Controls Engineer",
            "description_text": "Build control software.",
            "url": "https://example.com/jobs/controls",
        }
    ]
    assert len(evaluated_calls) == 1
    assert evaluated_calls[0]["jobs"] == [
        {"title": "Controls Engineer", "decision": "keep"}
    ]
    assert len(kept_calls) == 1
