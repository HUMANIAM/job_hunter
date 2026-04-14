from __future__ import annotations

from contextlib import contextmanager
from types import SimpleNamespace

from clients.job_downloader import Page, download_job_html_pages


def _yield(value: object):
    @contextmanager
    def _manager():
        yield value

    return _manager()


def test_download_job_html_pages_uses_adapter_transform(monkeypatch) -> None:
    opened_links: list[str] = []
    fake_page = object()
    fake_context = SimpleNamespace(new_page=lambda: fake_page)
    fake_browser = SimpleNamespace(new_context=lambda: _yield(fake_context))

    class FakeAdapter:
        def __init__(self) -> None:
            self.calls: list[tuple[str, str | None, str]] = []

        def transform_downloaded_html(
            self,
            *,
            url: str,
            title: str | None,
            html_content: str,
        ) -> tuple[str | None, str]:
            self.calls.append((url, title, html_content))
            return "Normalized Title", "<html><body>normalized</body></html>"

    adapter = FakeAdapter()

    monkeypatch.setattr(
        "clients.job_downloader.open_page",
        lambda page, link: opened_links.append(link),
    )
    monkeypatch.setattr(
        "clients.job_downloader.capture_page_title",
        lambda page: "Original Title",
    )
    monkeypatch.setattr(
        "clients.job_downloader.capture_page_html",
        lambda page: "<html><body>original</body></html>",
    )

    pages = download_job_html_pages(
        fake_browser,
        ["https://example.com/job/1"],
        adapter=adapter,
    )

    assert opened_links == ["https://example.com/job/1"]
    assert adapter.calls == [
        (
            "https://example.com/job/1",
            "Original Title",
            "<html><body>original</body></html>",
        )
    ]
    assert pages == [
        Page(
            url="https://example.com/job/1",
            title="Normalized Title",
            html_content="<html><body>normalized</body></html>",
        )
    ]
