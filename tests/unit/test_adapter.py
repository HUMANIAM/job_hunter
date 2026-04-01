from sources.sioux import adapter as sioux_adapter


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
    report = sioux_adapter.build_collection_validation_report(
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


def test_log_collection_validation_report_emits_expected_summary_lines(
    monkeypatch,
) -> None:
    # Given: a validation report with one mismatch on each side
    report = {
        "facet_union_unique_count": 3,
        "unfiltered_pagination_unique_count": 4,
        "only_in_facet_union_count": 1,
        "only_in_facet_union": ["https://example.com/facet-only"],
        "only_in_unfiltered_pagination_count": 1,
        "only_in_unfiltered_pagination": ["https://example.com/unfiltered-only"],
        "sets_exactly_equal": False,
    }
    messages: list[str] = []

    monkeypatch.setattr(sioux_adapter, "log", messages.append)

    # When: the adapter logs the validation report
    sioux_adapter.log_collection_validation_report(report)

    # Then: the key summary lines should be emitted in order
    assert messages == [
        "collection validation report",
        "facet_union_unique_count=3",
        "unfiltered_pagination_unique_count=4",
        "only_in_facet_union_count=1",
        "only_in_facet_union: https://example.com/facet-only",
        "only_in_unfiltered_pagination_count=1",
        "only_in_unfiltered_pagination: https://example.com/unfiltered-only",
        "sets_exactly_equal=False",
    ]


def test_collect_job_links_via_facets_tracks_disciplines_per_url(monkeypatch) -> None:
    # Given: overlapping facet results for the same vacancy URL
    class FakePage:
        url = sioux_adapter.START_URL

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

    monkeypatch.setattr(sioux_adapter, "wait_for_page_ready", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(sioux_adapter, "click_if_visible", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(
        sioux_adapter,
        "extract_discipline_facets",
        lambda _page: [
            ("Software", "https://example.com/software", 2),
            ("Electronics", "https://example.com/electronics", 2),
        ],
    )
    monkeypatch.setattr(
        sioux_adapter,
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
    job_links, discipline_map = sioux_adapter.collect_job_links_via_facets(
        FakeBrowser()
    )

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


def test_retrieve_sioux_job_links_returns_links_map_and_validation(
    monkeypatch,
) -> None:
    # Given: facet retrieval, unfiltered retrieval, and validation are available
    facet_links = ["https://vacancy.sioux.eu/vacancies/facet-job.html"]
    discipline_map = {
        "https://vacancy.sioux.eu/vacancies/facet-job.html": ["Software"]
    }
    validation_report = {
        "facet_union_unique_count": 1,
        "unfiltered_pagination_unique_count": 1,
        "only_in_facet_union_count": 0,
        "only_in_facet_union": [],
        "only_in_unfiltered_pagination_count": 0,
        "only_in_unfiltered_pagination": [],
        "sets_exactly_equal": True,
    }

    monkeypatch.setattr(
        sioux_adapter,
        "collect_job_links_via_facets",
        lambda _browser: (facet_links, discipline_map),
    )
    monkeypatch.setattr(
        sioux_adapter,
        "collect_job_links_via_unfiltered_pagination",
        lambda _browser: list(facet_links),
    )
    monkeypatch.setattr(
        sioux_adapter,
        "build_collection_validation_report",
        lambda facet_union_urls, unfiltered_pagination_urls: validation_report,
    )

    # When: the adapter builds the consolidated retrieval result
    retrieval = sioux_adapter.retrieve_sioux_job_links(object())

    # Then: main can consume links, discipline mapping, and validation directly
    assert retrieval.job_links == facet_links
    assert retrieval.discipline_map == discipline_map
    assert retrieval.validation_report == validation_report
