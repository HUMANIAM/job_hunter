from __future__ import annotations

from types import SimpleNamespace

from clients.sources import browser_listing_adapter as browser_listing_adapter_module
from clients.sources.browser_listing_adapter import (
    AdvanceDecision,
    BrowserListingAdapter,
    PageAdvance,
)


class UrlFollowingBrowserListingAdapter(BrowserListingAdapter):
    entry_url = "https://example.com/jobs"
    listing_label = "example listing"
    results_ready_selectors = ("a[href]",)
    next_page = object()

    def _get_job_links_from_page(
        self,
        page: object,
        log_context: str,
        *,
        job_limit: int,
    ) -> set[str]:
        return set()

    def _get_page_advance(self, page: object) -> PageAdvance:
        return PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://example.com/jobs?page=2",
        )

    def _collect_job_links_in_context(
        self,
        context: object,
        page: object,
        *,
        job_limit: int,
    ) -> list[str]:
        return []

    def _get_next_page(self, page: object, page_advance: PageAdvance) -> object:
        assert page_advance == PageAdvance(
            advance_decision=AdvanceDecision.FOLLOW_URL,
            next_page_url="https://example.com/jobs?page=2",
        )
        return self.next_page


def test_advance_decision_values_are_explicit() -> None:
    assert AdvanceDecision.FOLLOW_URL == "follow_url"
    assert AdvanceDecision.CLICK == "click"
    assert AdvanceDecision.STOP == "stop"


def test_page_advance_carries_both_advance_decision_and_next_page_url() -> None:
    page_advance = UrlFollowingBrowserListingAdapter()._get_page_advance(object())

    assert page_advance == PageAdvance(
        advance_decision=AdvanceDecision.FOLLOW_URL,
        next_page_url="https://example.com/jobs?page=2",
    )


def test_open_page_uses_shared_browser_listing_configuration(monkeypatch) -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page = SimpleNamespace(url="https://example.com/jobs?page=1")
    open_calls: list[tuple[object, str, tuple[str, ...], tuple[str, ...]]] = []
    messages: list[str] = []

    monkeypatch.setattr(
        browser_listing_adapter_module,
        "open_and_prepare_page",
        lambda page_obj, url, *, wait_for, click_if_visible_selectors: (
            open_calls.append(
                (
                    page_obj,
                    url,
                    tuple(wait_for),
                    tuple(click_if_visible_selectors),
                )
            )
            or ["button.cookie-accept"]
        ),
    )
    monkeypatch.setattr(browser_listing_adapter_module, "log", messages.append)
    adapter.cookie_accept_selectors = ("button.cookie-accept",)

    adapter._open_page(page, "https://example.com/jobs?page=1")

    assert open_calls == [
        (
            page,
            "https://example.com/jobs?page=1",
            ("a[href]",),
            ("button.cookie-accept",),
        )
    ]
    assert messages == [
        "accepted cookie banner selectors: ['button.cookie-accept']",
        "current page url: https://example.com/jobs?page=1",
    ]


def test_get_next_page_executes_page_advance_and_returns_next_page() -> None:
    adapter = UrlFollowingBrowserListingAdapter()
    page_advance = adapter._get_page_advance(object())

    assert adapter._get_next_page(object(), page_advance) is adapter.next_page
