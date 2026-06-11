from __future__ import annotations

from typing import Any

import pytest

from MVP.sources.api_listing_adapter import APIListingAdapter, APIPageResult
from infra import logging as infra_logging


class _TestAPIListingAdapter(APIListingAdapter):
    def __init__(self, *, max_attempts: int) -> None:
        self._max_attempts = max_attempts

    def _get_max_attempts(self) -> int:
        return self._max_attempts

    def _get_initial_request_state(self) -> Any:
        raise AssertionError("not used in this test")

    def _fetch_listing_response(self, request_state: Any) -> Any:
        raise AssertionError("not used in this test")

    def _parse_listing_response(
        self,
        response: Any,
        *,
        request_state: Any,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        raise AssertionError("not used in this test")


class _OverflowAPIListingAdapter(APIListingAdapter):
    def _get_initial_request_state(self) -> Any:
        return "page-1"

    def _fetch_listing_response(self, request_state: Any) -> Any:
        assert request_state == "page-1"
        return {}

    def _parse_listing_response(
        self,
        response: Any,
        *,
        request_state: Any,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        assert response == {}
        assert request_state == "page-1"
        assert page_index == 1
        assert remaining_job_budget == 5
        return APIPageResult(
            job_links={
                "https://example.com/job/a",
                "https://example.com/job/b",
                "https://example.com/job/c",
            },
            next_request_state=None,
            expected_total=2,
            is_last_page=True,
        )


class _NoNewLinksAPIListingAdapter(APIListingAdapter):
    def _get_max_attempts(self) -> int:
        return 1

    def _get_initial_request_state(self) -> Any:
        return 1

    def _fetch_listing_response(self, request_state: Any) -> Any:
        return request_state

    def _parse_listing_response(
        self,
        response: Any,
        *,
        request_state: Any,
        page_index: int,
        remaining_job_budget: int,
    ) -> APIPageResult:
        if request_state == 1:
            return APIPageResult(
                job_links={"https://example.com/job/a"},
                next_request_state=2,
                expected_total=3,
                is_last_page=False,
            )

        return APIPageResult(
            job_links={"https://example.com/job/a"},
            next_request_state=3,
            expected_total=3,
            is_last_page=False,
        )


def test_collect_job_links_accumulates_across_attempts_until_expected_total(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(infra_logging.time, "strftime", lambda _fmt: "12:34:56")
    adapter = _TestAPIListingAdapter(max_attempts=4)
    calls: list[int] = []
    attempts = iter(
        [
            ({"https://example.com/job/a"}, 3),
            ({"https://example.com/job/b"}, None),
            ({"https://example.com/job/c"}, None),
            ({"https://example.com/job/d"}, None),
        ]
    )

    def fake_collect_job_links_once(*, job_limit: int) -> tuple[set[str], int | None]:
        calls.append(job_limit)
        return next(attempts)

    monkeypatch.setattr(adapter, "_collect_job_links_once", fake_collect_job_links_once)

    links = adapter.collect_job_links(job_limit=5)

    assert links == [
        "https://example.com/job/a",
        "https://example.com/job/b",
        "https://example.com/job/c",
    ]
    assert calls == [5, 5, 5]
    assert (
        "reached expected total 3 across 3 attempts, stopping"
        in capsys.readouterr().out
    )


def test_collect_job_links_accumulates_across_attempts_until_job_limit(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(infra_logging.time, "strftime", lambda _fmt: "12:34:56")
    adapter = _TestAPIListingAdapter(max_attempts=4)
    calls: list[int] = []
    attempts = iter(
        [
            ({"https://example.com/job/a"}, 10),
            ({"https://example.com/job/b"}, None),
            ({"https://example.com/job/c"}, None),
        ]
    )

    def fake_collect_job_links_once(*, job_limit: int) -> tuple[set[str], int | None]:
        calls.append(job_limit)
        return next(attempts)

    monkeypatch.setattr(adapter, "_collect_job_links_once", fake_collect_job_links_once)

    links = adapter.collect_job_links(job_limit=2)

    assert links == [
        "https://example.com/job/a",
        "https://example.com/job/b",
    ]
    assert calls == [2, 2]
    assert "reached job limit 2 across 2 attempts, stopping" in capsys.readouterr().out


def test_collect_job_links_raises_when_attempt_exceeds_expected_total(
) -> None:
    adapter = _OverflowAPIListingAdapter()

    with pytest.raises(ValueError, match="collected more links than expected total"):
        adapter.collect_job_links(job_limit=5)


def test_collect_job_links_once_stops_when_page_adds_no_new_links(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(infra_logging.time, "strftime", lambda _fmt: "12:34:56")
    adapter = _NoNewLinksAPIListingAdapter()

    links = adapter.collect_job_links(job_limit=5)

    assert links == ["https://example.com/job/a"]
    assert "page yielded no new links, stopping" in capsys.readouterr().out
