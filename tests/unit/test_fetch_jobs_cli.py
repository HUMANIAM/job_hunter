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


def test_parse_args_defaults_to_optional_outputs_disabled() -> None:
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


class RaisingParser(FakeParser):
    def fetch_job(
        self,
        page: object,
        url: str,
        disciplines: list[str] | None = None,
        log_message=None,
    ) -> FakeJob | None:
        self.calls.append((page, url, disciplines or [], log_message))
        if url.endswith("/broken"):
            raise RuntimeError("llm failed")
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


def test_fetch_source_jobs_writes_only_match_by_default(monkeypatch) -> None:
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
    raw_writes: list[tuple[dict[str, object], str, object]] = []
    evaluated_writes: list[tuple[dict[str, object], str, object]] = []
    match_writes: list[tuple[dict[str, object], str, object]] = []

    monkeypatch.setattr(fetch_jobs, "log", messages.append)
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_validation_report",
        lambda report, *, company_slug, log_message: validation_writes.append(
            (report, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_raw_job",
        lambda payload, *, company_slug, log_message: raw_writes.append(
            (payload, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_evaluated_job",
        lambda payload, *, company_slug, log_message: evaluated_writes.append(
            (payload, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_match_job",
        lambda payload, *, company_slug, log_message: match_writes.append(
            (payload, company_slug, log_message)
        ),
    )

    result = fetch_jobs.fetch_source_jobs(browser, source)

    assert [job.url for job in result.jobs] == ["https://example.com/jobs/controls"]
    assert [job.url for job in result.matched_jobs] == [
        "https://example.com/jobs/controls"
    ]
    assert adapter.logged_reports == [validation_report]
    assert validation_writes == []
    assert raw_writes == []
    assert evaluated_writes == []
    assert len(match_writes) == 1
    assert match_writes[0][0]["url"] == "https://example.com/jobs/controls"
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
    assert messages[0:2] == [
        "fetch progress: [1/2]",
        "KEEP [1] 'Controls Engineer' | reason=title_keep_match | title_hits=['controls'] | description_hits=[]",
    ]
    assert messages[-1] == "closing browser after fetching 1 jobs"


def test_fetch_source_jobs_writes_requested_debug_artifacts(monkeypatch) -> None:
    retrieval = SourceRetrievalResult(
        job_links=["https://example.com/jobs/controls"],
        discipline_map={"https://example.com/jobs/controls": ["Control"]},
        validation_report={},
    )
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=FakeAdapter(retrieval),
        parser=FakeParser(),
    )
    browser = FakeBrowser()
    raw_writes: list[dict[str, object]] = []
    evaluated_writes: list[dict[str, object]] = []
    match_writes: list[dict[str, object]] = []

    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_raw_job",
        lambda payload, **_: raw_writes.append(payload),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_evaluated_job",
        lambda payload, **_: evaluated_writes.append(payload),
    )
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_match_job",
        lambda payload, **_: match_writes.append(payload),
    )

    fetch_jobs.fetch_source_jobs(
        browser,
        source,
        write_raw_jobs=True,
        write_evaluated_jobs=True,
    )

    assert len(raw_writes) == 1
    assert raw_writes[0]["url"] == "https://example.com/jobs/controls"
    assert len(evaluated_writes) == 1
    assert evaluated_writes[0]["decision"] == "keep"
    assert len(match_writes) == 1
    assert match_writes[0]["url"] == "https://example.com/jobs/controls"


def test_fetch_source_jobs_continues_after_single_job_failure(monkeypatch) -> None:
    retrieval = SourceRetrievalResult(
        job_links=[
            "https://example.com/jobs/broken",
            "https://example.com/jobs/controls",
        ],
        discipline_map={},
        validation_report={},
    )
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=FakeAdapter(retrieval),
        parser=RaisingParser(),
    )
    browser = FakeBrowser()
    messages: list[str] = []
    match_writes: list[dict[str, object]] = []

    monkeypatch.setattr(fetch_jobs, "log", messages.append)
    monkeypatch.setattr(
        fetch_jobs.report_writer,
        "write_match_job",
        lambda payload, **_: match_writes.append(payload),
    )
    monkeypatch.setattr(fetch_jobs.report_writer, "write_evaluated_job", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(fetch_jobs.report_writer, "write_raw_job", lambda *_args, **_kwargs: None)

    result = fetch_jobs.fetch_source_jobs(browser, source)

    assert [job.url for job in result.jobs] == ["https://example.com/jobs/controls"]
    assert len(match_writes) == 1
    assert match_writes[0]["url"] == "https://example.com/jobs/controls"
    assert any("job failed: url='https://example.com/jobs/broken'" in message for message in messages)


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


def test_main_writes_inline_job_states(monkeypatch) -> None:
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
    result = fetch_jobs.FetchSourceJobsResult(
        jobs=[
            FakeJob(
                title="Controls Engineer",
                description_text="Build control software.",
                url="https://example.com/jobs/controls",
            )
        ],
        matched_jobs=[
            FakeJob(
                title="Controls Engineer",
                description_text="Build control software.",
                url="https://example.com/jobs/controls",
            )
        ],
    )
    fetch_calls: list[bool] = []
    messages: list[str] = []

    monkeypatch.setattr(fetch_jobs, "get_source", lambda company: source)
    monkeypatch.setattr(
        fetch_jobs,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_calls.append(kwargs["write_validation_report"]) or result
        ),
    )
    monkeypatch.setattr(fetch_jobs, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        fetch_jobs,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(fetch_jobs, "log", messages.append)

    fetch_jobs.main([])

    assert fetch_calls == [False]
    assert messages[0] == "program started"
    assert messages[-1] == "done: total_jobs=1 | relevant_jobs=1 | elapsed_seconds=0.00"


def test_main_passes_validation_flag(monkeypatch) -> None:
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
    fetch_calls: list[bool] = []

    monkeypatch.setattr(fetch_jobs, "get_source", lambda company: source)
    monkeypatch.setattr(
        fetch_jobs,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_calls.append(kwargs["write_validation_report"])
            or fetch_jobs.FetchSourceJobsResult(jobs=[], matched_jobs=[])
        ),
    )
    monkeypatch.setattr(fetch_jobs, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        fetch_jobs,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(fetch_jobs, "log", lambda _message: None)

    fetch_jobs.main(["--write-validation"])

    assert fetch_calls == [True]


def test_main_passes_debug_output_flags(monkeypatch) -> None:
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
    fetch_kwargs: list[dict[str, bool]] = []

    monkeypatch.setattr(fetch_jobs, "get_source", lambda company: source)
    monkeypatch.setattr(
        fetch_jobs,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_kwargs.append(kwargs)
            or fetch_jobs.FetchSourceJobsResult(jobs=[], matched_jobs=[])
        ),
    )
    monkeypatch.setattr(fetch_jobs, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        fetch_jobs,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(fetch_jobs, "log", lambda _message: None)

    fetch_jobs.main(["--write-raw", "--write-evaluated"])

    assert fetch_kwargs == [
        {
            "write_raw_jobs": True,
            "write_evaluated_jobs": True,
            "write_validation_report": False,
        }
    ]
