from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
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

from app import job_hunter
from sources.base import SourceDefinition, SourceRetrievalResult


def test_parse_args_accepts_company_option() -> None:
    args = job_hunter.parse_args(["--company", "sioux"])

    assert args.company == "sioux"


def test_parse_args_defaults_to_optional_outputs_disabled() -> None:
    args = job_hunter.parse_args([])

    assert args.company == "sioux"
    assert args.candidate_profile == job_hunter.DEFAULT_CANDIDATE_PROFILE_PATH
    assert args.job_limit is None
    assert args.write_raw is False
    assert args.write_evaluated is False
    assert args.write_validation is False


def test_parse_args_accepts_candidate_profile_option() -> None:
    args = job_hunter.parse_args(
        ["--candidate-profile", "data/candidate_profiles/custom.json"]
    )

    assert args.candidate_profile == Path("data/candidate_profiles/custom.json")


def test_parse_args_accepts_cv_option() -> None:
    args = job_hunter.parse_args(["--cv", "data/candidate_profiles/custom.json"])

    assert args.candidate_profile == Path("data/candidate_profiles/custom.json")


def test_parse_args_accepts_job_limit_option() -> None:
    args = job_hunter.parse_args(["--job-limit", "1"])

    assert args.job_limit == 1


def test_parse_args_accepts_optional_output_flags() -> None:
    args = job_hunter.parse_args(
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
    job_id: str
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
            job_id="controls_engineer__test123456",
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
            job_id="controls_engineer__test123456",
            title="Controls Engineer",
            description_text="Build control software.",
            url=url,
        )


class FakeAdapter:
    def __init__(self, retrieval: SourceRetrievalResult) -> None:
        self.retrieval = retrieval
        self.logged_reports: list[dict[str, object]] = []
        self.retrieve_job_limits: list[int | None] = []

    def retrieve_job_links(
        self,
        browser: object,
        *,
        job_limit: int | None = None,
    ) -> SourceRetrievalResult:
        self.retrieve_job_limits.append(job_limit)
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


def _fake_candidate_profile() -> SimpleNamespace:
    return SimpleNamespace(candidate_id="Ibrahim_Saad_CV", profile=object())


def _fake_ranking_result(
    job: FakeJob,
    *,
    score: float = 0.91,
    candidate_id: str = "Ibrahim_Saad_CV",
) -> dict[str, object]:
    return {
        "job_id": job.job_id,
        "candidate_id": candidate_id,
        "score": score,
        "bucket_scores": {
            "skills": score,
            "languages": 0.8,
            "protocols": 0.7,
            "standards": 0.0,
            "domains": 0.6,
            "seniority": 0.9,
            "years_experience": 0.8,
        },
        "matched_features": [],
        "missing_features": [],
    }


def _patch_ranker(monkeypatch, *, messages: list[str] | None = None) -> None:
    def fake_rank_jobs(candidate_profile, jobs, *, log_message):
        if messages is not None and jobs:
            log_message(
                "RANK [1] 'Controls Engineer' | score=0.910 | "
                "skills=0.910 | languages=0.800 | protocols=0.700 | "
                "standards=0.000 | domains=0.600 | seniority=0.900 | "
                "years_experience=0.800"
            )
        return SimpleNamespace(
            results=[_fake_ranking_result(job) for job in jobs],
            ranked_jobs=list(jobs),
        )

    monkeypatch.setattr(job_hunter, "rank_jobs", fake_rank_jobs)


def test_load_candidate_profile_backfills_candidate_id_from_filename(tmp_path: Path) -> None:
    candidate_profile_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_profile_path.write_text(
        json.dumps(
            {
                "source_text_hash": "3a01ac116f682c78fdd0704ed2774349959633d1a81647b79ecd1c396f6443d1",
                "schema_version": "2.0.0",
                "profile": {
                    "skills": [],
                    "languages": [],
                    "protocols": [],
                    "standards": [],
                    "domains": [],
                    "seniority": {
                        "value": None,
                        "confidence": 0.0,
                        "evidence": [],
                    },
                    "years_experience_total": {
                        "value": None,
                        "confidence": 0.0,
                        "evidence": [],
                    },
                    "candidate_constraints": {
                        "preferred_locations": [],
                        "excluded_locations": [],
                        "preferred_workplace_types": [],
                        "excluded_workplace_types": [],
                        "requires_visa_sponsorship": None,
                        "avoid_export_control_roles": None,
                        "notes": [],
                        "confidence": 0.0,
                        "evidence": [],
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    candidate_profile = job_hunter.load_candidate_profile(candidate_profile_path)

    assert candidate_profile.candidate_id == "Ibrahim_Saad_CV"


def test_fetch_source_jobs_writes_rankings_by_default(monkeypatch) -> None:
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
    ranking_writes: list[tuple[dict[str, object], object]] = []

    monkeypatch.setattr(job_hunter, "log", messages.append)
    _patch_ranker(monkeypatch, messages=messages)
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_validation_report",
        lambda report, *, company_slug, log_message: validation_writes.append(
            (report, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_raw_job",
        lambda payload, *, company_slug, log_message: raw_writes.append(
            (payload, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_evaluated_job",
        lambda payload, *, company_slug, log_message: evaluated_writes.append(
            (payload, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_ranking_result",
        lambda payload, *, log_message: ranking_writes.append((payload, log_message)),
    )

    result = job_hunter.fetch_source_jobs(
        browser,
        source,
        candidate_profile=_fake_candidate_profile(),
    )

    assert [job.url for job in result.jobs] == ["https://example.com/jobs/controls"]
    assert [job.url for job in result.ranked_jobs] == [
        "https://example.com/jobs/controls"
    ]
    assert result.ranking_results[0]["job_id"] == "controls_engineer__test123456"
    assert result.ranking_results[0]["candidate_id"] == "Ibrahim_Saad_CV"
    assert adapter.retrieve_job_limits == [None]
    assert adapter.logged_reports == [validation_report]
    assert validation_writes == []
    assert raw_writes == []
    assert evaluated_writes == []
    assert len(ranking_writes) == 1
    assert ranking_writes[0][0]["job_id"] == "controls_engineer__test123456"
    assert ranking_writes[0][0]["candidate_id"] == "Ibrahim_Saad_CV"
    assert parser.calls == [
        (
            browser.context.page,
            "https://example.com/jobs/controls",
            ["Control"],
            job_hunter.log,
        ),
        (
            browser.context.page,
            "https://example.com/jobs/skip",
            [],
            job_hunter.log,
        ),
    ]
    assert browser.context.closed is True
    assert messages[:2] == ["fetch progress: [1/2]", "fetch progress: [2/2]"]
    assert any(message.startswith("RANK [1] 'Controls Engineer' | score=0.910") for message in messages)
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
    ranking_writes: list[dict[str, object]] = []

    _patch_ranker(monkeypatch)
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_raw_job",
        lambda payload, **_: raw_writes.append(payload),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_evaluated_job",
        lambda payload, **_: evaluated_writes.append(payload),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_ranking_result",
        lambda payload, **_: ranking_writes.append(payload),
    )

    job_hunter.fetch_source_jobs(
        browser,
        source,
        candidate_profile=_fake_candidate_profile(),
        write_raw_jobs=True,
        write_evaluated_jobs=True,
    )

    assert len(raw_writes) == 1
    assert raw_writes[0]["job_id"] == "controls_engineer__test123456"
    assert raw_writes[0]["url"] == "https://example.com/jobs/controls"
    assert len(evaluated_writes) == 1
    assert evaluated_writes[0]["job_id"] == "controls_engineer__test123456"
    assert evaluated_writes[0]["ranking"]["candidate_id"] == "Ibrahim_Saad_CV"
    assert len(ranking_writes) == 1
    assert ranking_writes[0]["job_id"] == "controls_engineer__test123456"
    assert ranking_writes[0]["candidate_id"] == "Ibrahim_Saad_CV"


def test_fetch_source_jobs_passes_job_limit_to_adapter(monkeypatch) -> None:
    retrieval = SourceRetrievalResult(
        job_links=["https://example.com/jobs/controls"],
        discipline_map={},
        validation_report={},
    )
    adapter = FakeAdapter(retrieval)
    source = SourceDefinition(
        company_slug="sioux",
        source_url="https://example.com/jobs",
        configured_countries=("Netherlands",),
        configured_languages=("en",),
        adapter=adapter,
        parser=FakeParser(),
    )
    browser = FakeBrowser()

    _patch_ranker(monkeypatch)
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_ranking_result",
        lambda *_args, **_kwargs: None,
    )

    job_hunter.fetch_source_jobs(
        browser,
        source,
        candidate_profile=_fake_candidate_profile(),
        job_limit=1,
    )

    assert adapter.retrieve_job_limits == [1]


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
    ranking_writes: list[dict[str, object]] = []

    monkeypatch.setattr(job_hunter, "log", messages.append)
    _patch_ranker(monkeypatch)
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_ranking_result",
        lambda payload, **_: ranking_writes.append(payload),
    )

    result = job_hunter.fetch_source_jobs(
        browser,
        source,
        candidate_profile=_fake_candidate_profile(),
    )

    assert [job.url for job in result.jobs] == ["https://example.com/jobs/controls"]
    assert len(ranking_writes) == 1
    assert ranking_writes[0]["job_id"] == "controls_engineer__test123456"
    assert ranking_writes[0]["candidate_id"] == "Ibrahim_Saad_CV"
    assert any(
        "job failed: url='https://example.com/jobs/broken'" in message
        for message in messages
    )


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

    _patch_ranker(monkeypatch)
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_validation_report",
        lambda report, *, company_slug, log_message: validation_writes.append(
            (report, company_slug, log_message)
        ),
    )
    monkeypatch.setattr(
        job_hunter.report_writer,
        "write_ranking_result",
        lambda *_args, **_kwargs: None,
    )

    job_hunter.fetch_source_jobs(
        browser,
        source,
        candidate_profile=_fake_candidate_profile(),
        write_validation_report=True,
    )

    assert adapter.logged_reports == [validation_report]
    assert validation_writes == [(validation_report, "sioux", job_hunter.log)]


@contextmanager
def _yield(value: object):
    yield value


def test_main_loads_candidate_profile_and_logs_summary(monkeypatch) -> None:
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
    candidate_profile = _fake_candidate_profile()
    result = job_hunter.FetchSourceJobsResult(
        jobs=[
            FakeJob(
                job_id="controls_engineer__test123456",
                title="Controls Engineer",
                description_text="Build control software.",
                url="https://example.com/jobs/controls",
            )
        ],
        ranking_results=[
            _fake_ranking_result(
                FakeJob(
                    job_id="controls_engineer__test123456",
                    title="Controls Engineer",
                    description_text="Build control software.",
                    url="https://example.com/jobs/controls",
                )
            )
        ],
        ranked_jobs=[
            FakeJob(
                job_id="controls_engineer__test123456",
                title="Controls Engineer",
                description_text="Build control software.",
                url="https://example.com/jobs/controls",
            )
        ],
    )
    fetch_kwargs: list[dict[str, object]] = []
    messages: list[str] = []

    monkeypatch.setattr(job_hunter, "get_source", lambda company: source)
    monkeypatch.setattr(
        job_hunter,
        "load_candidate_profile",
        lambda path: candidate_profile,
    )
    monkeypatch.setattr(
        job_hunter,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_kwargs.append(kwargs) or result
        ),
    )
    monkeypatch.setattr(job_hunter, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        job_hunter,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(job_hunter, "log", messages.append)

    job_hunter.main([])

    assert fetch_kwargs == [
        {
            "candidate_profile": candidate_profile,
            "job_limit": None,
            "write_raw_jobs": False,
            "write_evaluated_jobs": False,
            "write_validation_report": False,
        }
    ]
    assert messages[0] == "program started"
    assert messages[-1] == "done: total_jobs=1 | ranked_jobs=1 | elapsed_seconds=0.00"


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
    candidate_profile = _fake_candidate_profile()
    fetch_calls: list[bool] = []

    monkeypatch.setattr(job_hunter, "get_source", lambda company: source)
    monkeypatch.setattr(
        job_hunter,
        "load_candidate_profile",
        lambda path: candidate_profile,
    )
    monkeypatch.setattr(
        job_hunter,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_calls.append(kwargs["write_validation_report"])
            or job_hunter.FetchSourceJobsResult(
                jobs=[],
                ranking_results=[],
                ranked_jobs=[],
            )
        ),
    )
    monkeypatch.setattr(job_hunter, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        job_hunter,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(job_hunter, "log", lambda _message: None)

    job_hunter.main(["--write-validation"])

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
    candidate_profile = _fake_candidate_profile()
    fetch_kwargs: list[dict[str, object]] = []

    monkeypatch.setattr(job_hunter, "get_source", lambda company: source)
    monkeypatch.setattr(
        job_hunter,
        "load_candidate_profile",
        lambda path: candidate_profile,
    )
    monkeypatch.setattr(
        job_hunter,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_kwargs.append(kwargs)
            or job_hunter.FetchSourceJobsResult(
                jobs=[],
                ranking_results=[],
                ranked_jobs=[],
            )
        ),
    )
    monkeypatch.setattr(job_hunter, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        job_hunter,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(job_hunter, "log", lambda _message: None)

    job_hunter.main(["--write-raw", "--write-evaluated"])

    assert fetch_kwargs == [
        {
            "candidate_profile": candidate_profile,
            "job_limit": None,
            "write_raw_jobs": True,
            "write_evaluated_jobs": True,
            "write_validation_report": False,
        }
    ]


def test_main_passes_job_limit_flag(monkeypatch) -> None:
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
    candidate_profile = _fake_candidate_profile()
    fetch_kwargs: list[dict[str, object]] = []

    monkeypatch.setattr(job_hunter, "get_source", lambda company: source)
    monkeypatch.setattr(
        job_hunter,
        "load_candidate_profile",
        lambda path: candidate_profile,
    )
    monkeypatch.setattr(
        job_hunter,
        "fetch_source_jobs",
        lambda browser, resolved_source, **kwargs: (
            fetch_kwargs.append(kwargs)
            or job_hunter.FetchSourceJobsResult(
                jobs=[],
                ranking_results=[],
                ranked_jobs=[],
            )
        ),
    )
    monkeypatch.setattr(job_hunter, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        job_hunter,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(object()),
    )
    monkeypatch.setattr(job_hunter, "log", lambda _message: None)

    job_hunter.main(["--company", "sioux", "--job-limit", "1"])

    assert fetch_kwargs == [
        {
            "candidate_profile": candidate_profile,
            "job_limit": 1,
            "write_raw_jobs": False,
            "write_evaluated_jobs": False,
            "write_validation_report": False,
        }
    ]
