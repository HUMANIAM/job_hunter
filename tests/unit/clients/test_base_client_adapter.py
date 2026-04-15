from __future__ import annotations

from contextlib import contextmanager

from clients.base import BaseClientAdapter


class _FakePage:
    pass


class _FakeContext:
    def __init__(self) -> None:
        self.page = _FakePage()
        self.new_page_calls = 0

    def new_page(self) -> _FakePage:
        self.new_page_calls += 1
        return self.page


class _FakeBrowser:
    def __init__(self) -> None:
        self.context = _FakeContext()
        self.new_context_calls = 0

    def new_context(self):
        self.new_context_calls += 1

        @contextmanager
        def _manager():
            yield self.context

        return _manager()


class _ConcreteAdapter(BaseClientAdapter):
    def __init__(self) -> None:
        self.calls: list[tuple[object, int]] = []

    def _collect_job_links_in_context(
        self,
        context: object,
        *,
        job_limit: int,
    ) -> list[str]:
        self.calls.append((context, job_limit))
        return ["https://example.com/job-1"]


def test_collect_job_links_opens_one_context() -> None:
    adapter = _ConcreteAdapter()
    browser = _FakeBrowser()

    result = adapter.collect_job_links(browser, job_limit=3)

    assert result == ["https://example.com/job-1"]
    assert browser.new_context_calls == 1
    assert browser.context.new_page_calls == 0
    assert adapter.calls == [(browser.context, 3)]
