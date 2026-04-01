import json
from pathlib import Path

import fetch_jobs


def test_matched_keywords_uses_boundaries_for_short_keywords() -> None:
    # Given: a short keyword that previously matched inside a larger token
    patterns = fetch_jobs.compile_keyword_patterns(["ml"])

    # When: the helper scans unrelated text
    matched_in_asml = fetch_jobs.matched_keywords(
        "ASML careers portal", ["ml"], patterns
    )
    matched_in_ml_text = fetch_jobs.matched_keywords(
        "Experience with ML inference systems.", ["ml"], patterns
    )

    # Then: only the standalone ML mention should match
    assert matched_in_asml == []
    assert matched_in_ml_text == ["ml"]


def test_evaluate_job_skips_only_by_title() -> None:
    # Given: a software title with non-target business words in the description
    job = fetch_jobs.Job(
        title="Controls Scientist",
        url="https://example.com/controls-scientist",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text=(
            "Build machine control software for lithography systems and "
            "partner with finance and supply chain stakeholders."
        ),
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: the description should not trigger a hard reject
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "title_keep_match"
    assert evaluation["title_hits"] == ["controls"]


def test_evaluate_job_rejects_skip_title_keyword() -> None:
    # Given: a title that is clearly outside the target profile
    job = fetch_jobs.Job(
        title="Supply Chain Planner",
        url="https://example.com/supply-chain-planner",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text="Python dashboards and automation for operations.",
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: the skip title keyword should override keep terms
    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "skip_title_keywords"
    assert evaluation["skip_hits"] == ["supply chain", "planner"]


def test_evaluate_job_rejects_low_signal_description_only_match() -> None:
    # Given: a non-target title with only a generic description keyword
    job = fetch_jobs.Job(
        title="Accounts Payable Specialist",
        url="https://example.com/accounts-payable-specialist",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text="The team is focused on control processes and approvals.",
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: a single low-signal description hit should not keep the job
    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "insufficient_keep_signal"
    assert evaluation["description_hits"] == []


def test_evaluate_job_keeps_strong_description_only_match() -> None:
    # Given: an ambiguous title with multiple strong technical description hits
    job = fetch_jobs.Job(
        title="Process Improvement Role",
        url="https://example.com/process-improvement-role",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text=(
            "Build Python tooling for Linux-based systems and machine learning "
            "inference workflows."
        ),
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: multiple strong description hits should keep the job
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "description_keep_match"
    assert evaluation["description_hits"] == [
        "python",
        "linux",
        "machine learning",
        "inference",
    ]


def test_sioux_output_paths_use_analysis_directory() -> None:
    # Given: the scraper's configured output location
    expected_dir = Path("data/analysis/sioux")

    # Then: all Sioux artifact paths should resolve under the analysis folder
    assert fetch_jobs.OUTPUT_DIR == expected_dir
    assert fetch_jobs.RAW_OUTPUT_PATH == expected_dir / "jobs_sioux_raw.json"
    assert fetch_jobs.EVALUATED_OUTPUT_PATH == expected_dir / "jobs_sioux_evaluated.json"
    assert fetch_jobs.OUTPUT_PATH == expected_dir / "jobs_sioux.json"
    assert fetch_jobs.VALIDATION_OUTPUT_PATH == expected_dir / "jobs_sioux_validation.json"


def test_write_json_creates_parent_directories(tmp_path: Path) -> None:
    # Given: a nested output path that does not exist yet
    output_path = tmp_path / "data" / "analysis" / "sioux" / "sample.json"

    # When: the helper writes a payload
    fetch_jobs.write_json(output_path, {"ok": True})

    # Then: the parent folders and file should exist with the payload
    assert output_path.exists()
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == {"ok": True}


def test_build_collection_validation_report_compares_both_sets() -> None:
    # Given: two collectors with one shared and one mismatched URL each
    facet_union_urls = [
        "https://vacancy.sioux.eu/vacancies/shared.html",
        "https://vacancy.sioux.eu/vacancies/facet-only.html",
    ]
    unfiltered_pagination_urls = [
        "https://vacancy.sioux.eu/vacancies/shared.html",
        "https://vacancy.sioux.eu/vacancies/unfiltered-only.html",
    ]

    # When: the validation report is built
    report = fetch_jobs.build_collection_validation_report(
        facet_union_urls=facet_union_urls,
        unfiltered_pagination_urls=unfiltered_pagination_urls,
    )

    # Then: the exact mismatches and counts should be preserved
    assert report["facet_union_unique_count"] == 2
    assert report["unfiltered_pagination_unique_count"] == 2
    assert report["only_in_facet_union"] == [
        "https://vacancy.sioux.eu/vacancies/facet-only.html"
    ]
    assert report["only_in_unfiltered_pagination"] == [
        "https://vacancy.sioux.eu/vacancies/unfiltered-only.html"
    ]
    assert report["sets_exactly_equal"] is False


def test_parse_job_posting_json_ld_blocks_extracts_location_country() -> None:
    # Given: a JobPosting schema block with location metadata
    json_ld_blocks = [
        json.dumps(
            {
                "@context": "https://schema.org/",
                "@type": "JobPosting",
                "jobLocation": {
                    "address": {
                        "addressLocality": "Eindhoven",
                        "addressCountry": "NL",
                    }
                },
                "employmentType": "Full time",
            }
        )
    ]

    # When: the structured metadata is parsed
    metadata = fetch_jobs.parse_job_posting_json_ld_blocks(json_ld_blocks)

    # Then: the structured location fields should be available
    assert metadata == {
        "location": "Eindhoven",
        "country": "NL",
        "employment_type": "Full time",
    }


def test_resolve_job_metadata_prefers_job_tags(monkeypatch) -> None:
    # Given: job-tag metadata and a schema fallback with overlapping fields
    monkeypatch.setattr(
        fetch_jobs,
        "extract_job_tags",
        lambda _page: {
            "location": "Eindhoven",
            "employment": "Full time",
            "education level": "Bachelor",
        },
    )
    monkeypatch.setattr(
        fetch_jobs,
        "extract_job_posting_metadata",
        lambda _page: {
            "location": "Fallback City",
            "country": "NL",
            "employment_type": "Fallback employment",
        },
    )

    # When: the metadata is resolved for a vacancy page
    metadata = fetch_jobs.resolve_job_metadata(object())

    # Then: explicit job tags should win, with schema data kept as fallback
    assert metadata == {
        "location": "Eindhoven",
        "country": "NL",
        "educational_background": "Bachelor",
        "fulltime_parttime": "Full time",
    }


def test_collect_job_links_via_facets_tracks_disciplines_per_url(monkeypatch) -> None:
    # Given: overlapping facet results for the same vacancy URL
    class FakePage:
        url = fetch_jobs.START_URL

        def goto(self, *_args, **_kwargs) -> None:
            return None

    class FakeContext:
        def new_page(self) -> FakePage:
            return FakePage()

        def close(self) -> None:
            return None

    class FakeBrowser:
        def new_context(self) -> FakeContext:
            return FakeContext()

    monkeypatch.setattr(fetch_jobs, "wait_for_results", lambda _page: None)
    monkeypatch.setattr(
        fetch_jobs, "close_cookie_banner_if_present", lambda _page: None
    )
    monkeypatch.setattr(
        fetch_jobs,
        "extract_discipline_facets",
        lambda _page: [
            ("Software", "https://example.com/software", 2),
            ("Electronics", "https://example.com/electronics", 2),
        ],
    )
    monkeypatch.setattr(
        fetch_jobs,
        "collect_links_for_facet",
        lambda _browser, facet_name, _facet_url, _expected_count: {
            "Software": {
                "https://vacancy.sioux.eu/vacancies/shared.html",
                "https://vacancy.sioux.eu/vacancies/software-only.html",
            },
            "Electronics": {
                "https://vacancy.sioux.eu/vacancies/electronics-only.html",
                "https://vacancy.sioux.eu/vacancies/shared.html",
            },
        }[facet_name],
    )

    # When: the facet collector merges all links
    job_links, discipline_map = fetch_jobs.collect_job_links_via_facets(FakeBrowser())

    # Then: overlapping URLs should keep all contributing disciplines
    assert job_links == [
        "https://vacancy.sioux.eu/vacancies/electronics-only.html",
        "https://vacancy.sioux.eu/vacancies/shared.html",
        "https://vacancy.sioux.eu/vacancies/software-only.html",
    ]
    assert discipline_map["https://vacancy.sioux.eu/vacancies/shared.html"] == [
        "Electronics",
        "Software",
    ]
    assert discipline_map["https://vacancy.sioux.eu/vacancies/software-only.html"] == [
        "Software"
    ]
