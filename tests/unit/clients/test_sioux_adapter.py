from __future__ import annotations

from types import ModuleType
import sys

if "playwright.sync_api" not in sys.modules:
    sync_api = ModuleType("playwright.sync_api")
    sync_api.sync_playwright = lambda: None
    sync_api.Browser = object
    sync_api.Page = object
    sync_api.Playwright = object

    playwright = ModuleType("playwright")
    playwright.sync_api = sync_api

    sys.modules["playwright"] = playwright
    sys.modules["playwright.sync_api"] = sync_api

from clients.sources.browser_listing_adapter import AdvanceDecision, PageAdvance
from clients.sources.sioux.adapter import SiouxBrowserListingAdapter


class _FakePage:
    pass


class _MutablePage:
    def __init__(self, url: str) -> None:
        self.url = url


class _MissingElement:
    def count(self) -> int:
        return 0

    def get_attribute(self, name: str) -> None:
        return None


class _FakeNextElement:
    def __init__(self, href: str | None) -> None:
        self.href = href

    def count(self) -> int:
        return 1

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


class _FakeSelectorResult:
    def __init__(self, element: _FakeNextElement | _MissingElement | None = None) -> None:
        self.first = element if element is not None else _MissingElement()


class _FakePaginationPage:
    def __init__(self, next_href: str | None = None) -> None:
        self._next_href = next_href

    def locator(self, selector: str):
        if selector == "div.overview-paging-controls a.paging-item-next":
            if self._next_href is None:
                return _FakeSelectorResult()
            return _FakeSelectorResult(_FakeNextElement(self._next_href))
        assert selector == "a.act-item-job-overview"
        return _FakeListingAnchorList([])


class _FakeListingAnchor:
    def __init__(self, href: str | None) -> None:
        self.href = href

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self.href


class _FakeListingAnchorList:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._anchors = [_FakeListingAnchor(href) for href in hrefs]

    def count(self) -> int:
        return len(self._anchors)

    def nth(self, index: int) -> _FakeListingAnchor:
        return self._anchors[index]


class _FakeListingPage:
    def __init__(self, hrefs: list[str | None]) -> None:
        self._hrefs = hrefs

    def locator(self, selector: str) -> _FakeListingAnchorList:
        assert selector == "a.act-item-job-overview"
        return _FakeListingAnchorList(self._hrefs)


class _FakeFacetText:
    def __init__(self, text: str) -> None:
        self._text = text

    def inner_text(self) -> str:
        return self._text


class _FakeFacetLink:
    def __init__(self, *, name: str, count_text: str, href: str | None) -> None:
        self._name = name
        self._count_text = count_text
        self._href = href

    def locator(self, selector: str) -> _FakeFacetText:
        if selector == ".filter-item-link-name":
            return _FakeFacetText(self._name)
        if selector == ".filter-item-link-count":
            return _FakeFacetText(self._count_text)
        raise AssertionError(f"unexpected selector: {selector}")

    def get_attribute(self, name: str) -> str | None:
        assert name == "href"
        return self._href


class _FakeFacetLinkList:
    def __init__(self, links: list[_FakeFacetLink]) -> None:
        self._links = links

    def count(self) -> int:
        return len(self._links)

    def nth(self, index: int) -> _FakeFacetLink:
        return self._links[index]


class _FakeFacetPage:
    def __init__(self, links: list[_FakeFacetLink]) -> None:
        self._links = links

    def locator(self, selector: str) -> _FakeFacetLinkList:
        assert selector == "div.facets_item[data-type='functiegr'] a.filter-item-link"
        return _FakeFacetLinkList(self._links)


class _FakeContext:
    def __init__(self) -> None:
        self.page = _FakePage()

    def new_page(self) -> _FakePage:
        return self.page


class _FakeBrowser:
    def __init__(self) -> None:
        self.context = _FakeContext()

    def new_context(self):
        class _Manager:
            def __enter__(self_nonlocal):
                return self.context

            def __exit__(self_nonlocal, exc_type, exc, tb):
                return None

        return _Manager()


def test_sioux_browser_listing_adapter_uses_typed_default_returns(
    monkeypatch,
) -> None:
    adapter = SiouxBrowserListingAdapter()
    browser = _FakeBrowser()
    page = object()
    monkeypatch.setattr(adapter, "_extract_discipline_facets", lambda page_obj: [])
    monkeypatch.setattr(adapter, "_open_page", lambda page_obj, url: None)

    assert adapter.collect_job_links(browser, job_limit=10) == []
    assert adapter._get_page_advance(_FakePaginationPage()) == PageAdvance(
        advance_decision=AdvanceDecision.STOP,
    )
    assert adapter._get_next_page(page, PageAdvance(
        advance_decision=AdvanceDecision.FOLLOW_URL,
        next_page_url="https://vacancy.sioux.eu/vacancies?page=2",
    )) is page


def test_extract_discipline_facets_normalizes_names_and_resolves_urls() -> None:
    adapter = SiouxBrowserListingAdapter()
    page = _FakeFacetPage(
        [
            _FakeFacetLink(
                name="  Embedded   Software  ",
                count_text=" 12 ",
                href="/vacancies/embedded-software-engineer.html",
            ),
            _FakeFacetLink(
                name="Mechatronics",
                count_text="open",
                href="vacancies/mechatronics-system-engineer.html",
            ),
            _FakeFacetLink(
                name="Ignored",
                count_text="3",
                href=None,
            ),
        ]
    )

    facets = adapter._extract_discipline_facets(page)

    assert facets == [
        (
            "Embedded Software",
            "https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
            12,
        ),
        (
            "Mechatronics",
            "https://vacancy.sioux.eu/vacancies/mechatronics-system-engineer.html",
            -1,
        ),
    ]


def test_get_job_links_from_page_keeps_live_sioux_job_urls() -> None:
    adapter = SiouxBrowserListingAdapter()
    page = _FakeListingPage(
        [
            "/vacancies/embedded-software-engineer.html",
            "https://vacancy.sioux.eu/vacancies/system-architect.html",
            "/",
            None,
        ]
    )

    links = adapter._get_job_links_from_page(
        page,
        "sioux page 1",
        job_limit=10,
    )

    assert links == {
        "https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        "https://vacancy.sioux.eu/vacancies/system-architect.html",
    }


def test_get_page_advance_resolves_relative_next_link() -> None:
    adapter = SiouxBrowserListingAdapter()
    page = _FakePaginationPage("/vacancies?page=2")

    page_advance = adapter._get_page_advance(page)

    assert page_advance == PageAdvance(
        advance_decision=AdvanceDecision.FOLLOW_URL,
        next_page_url="https://vacancy.sioux.eu/vacancies?page=2",
    )


def test_get_next_page_opens_follow_url_and_returns_same_page(
    monkeypatch,
) -> None:
    adapter = SiouxBrowserListingAdapter()
    page = object()
    open_calls: list[tuple[object, str]] = []

    monkeypatch.setattr(
        adapter,
        "_open_page",
        lambda page_obj, url: open_calls.append((page_obj, url)),
    )

    next_page = adapter._get_next_page(
        page,
        PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://vacancy.sioux.eu/vacancies?page=2",
        ),
    )

    assert next_page is page
    assert open_calls == [(page, "https://vacancy.sioux.eu/vacancies?page=2")]


def test_collect_links_from_paginated_listing_follows_next_pages_until_stop(
    monkeypatch,
) -> None:
    adapter = SiouxBrowserListingAdapter()
    page = _MutablePage("https://vacancy.sioux.eu/vacancies?page=1")
    transitions: list[str] = []

    monkeypatch.setattr(
        adapter,
        "_get_job_links_from_page",
        lambda page_obj, log_context, *, job_limit: {
            "https://vacancy.sioux.eu/vacancies?page=1": {
                "https://vacancy.sioux.eu/vacancies/software-only.html",
            },
            "https://vacancy.sioux.eu/vacancies?page=2": {
                "https://vacancy.sioux.eu/vacancies/electronics-only.html",
            },
        }[page_obj.url],
    )
    monkeypatch.setattr(
        adapter,
        "_get_page_advance",
        lambda page_obj: (
            PageAdvance(
                advance_decision=AdvanceDecision.FOLLOW_URL,
                next_page_url="https://vacancy.sioux.eu/vacancies?page=2",
            )
            if page_obj.url == "https://vacancy.sioux.eu/vacancies?page=1"
            else PageAdvance(advance_decision=AdvanceDecision.STOP)
        ),
    )
    monkeypatch.setattr(
        adapter,
        "_get_next_page",
        lambda page_obj, page_advance: (
            transitions.append(page_advance.next_page_url or "")
            or setattr(page_obj, "url", page_advance.next_page_url)
            or page_obj
        ),
    )

    links = adapter._collect_links_from_paginated_listing(
        page,
        "facet 'Software'",
        expected_count=2,
        job_limit=10,
    )

    assert links == {
        "https://vacancy.sioux.eu/vacancies/software-only.html",
        "https://vacancy.sioux.eu/vacancies/electronics-only.html",
    }
    assert transitions == ["https://vacancy.sioux.eu/vacancies?page=2"]


def test_collect_links_for_facet_uses_paginated_listing(monkeypatch) -> None:
    adapter = SiouxBrowserListingAdapter()
    page = object()
    open_calls: list[tuple[object, str]] = []
    listing_calls: list[tuple[object, str, int, int]] = []

    monkeypatch.setattr(
        adapter,
        "_open_page",
        lambda page_obj, url: open_calls.append((page_obj, url)),
    )
    monkeypatch.setattr(
        adapter,
        "_collect_links_from_paginated_listing",
        lambda page_obj, context, expected_count=None, *, job_limit: (
            listing_calls.append((page_obj, context, expected_count, job_limit))
            or {"https://vacancy.sioux.eu/vacancies/software-only.html"}
        ),
    )

    links = adapter._collect_links_for_facet(
        page,
        "Software",
        "https://example.com/software",
        4,
        job_limit=7,
    )

    assert links == {"https://vacancy.sioux.eu/vacancies/software-only.html"}
    assert open_calls == [(page, "https://example.com/software")]
    assert listing_calls == [(page, "facet 'Software'", 4, 7)]


def test_collect_job_links_in_context_reuses_single_page_for_facets(
    monkeypatch,
) -> None:
    adapter = SiouxBrowserListingAdapter()
    context = _FakeContext()
    page = context.page
    facet_calls: list[tuple[object, str, int]] = []

    monkeypatch.setattr(adapter, "_open_page", lambda page_obj, url: None)
    monkeypatch.setattr(
        adapter,
        "_extract_discipline_facets",
        lambda page_obj: [
            ("Software", "https://example.com/software", 2),
            ("Electronics", "https://example.com/electronics", 1),
        ],
    )
    monkeypatch.setattr(
        adapter,
        "_collect_links_for_facet",
        lambda page_obj, facet_name, facet_url, expected_count, *, job_limit: (
            facet_calls.append((page_obj, facet_name, job_limit))
            or {
                "Software": {"https://vacancy.sioux.eu/vacancies/software-only.html"},
                "Electronics": {
                    "https://vacancy.sioux.eu/vacancies/electronics-only.html"
                },
            }[facet_name]
        ),
    )

    job_links = adapter._collect_job_links_in_context(context, job_limit=10)

    assert job_links == [
        "https://vacancy.sioux.eu/vacancies/electronics-only.html",
        "https://vacancy.sioux.eu/vacancies/software-only.html",
    ]
    assert facet_calls == [
        (page, "Software", 10),
        (page, "Electronics", 9),
    ]
