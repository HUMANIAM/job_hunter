from __future__ import annotations

from pathlib import Path
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

from clients.job_downloader import download_job_html_pages
from reporting.writer import raw_html_filename


class FakePage:
    def __init__(self, html_by_url: dict[str, str], title_by_url: dict[str, str]) -> None:
        self.html_by_url = html_by_url
        self.title_by_url = title_by_url
        self.current_url: str | None = None

    def goto(self, url: str, *, wait_until: str, timeout: int) -> None:
        self.current_url = url

    def content(self) -> str:
        assert self.current_url is not None
        return self.html_by_url[self.current_url]

    def title(self) -> str:
        assert self.current_url is not None
        return self.title_by_url[self.current_url]


class FakeContext:
    def __init__(self, html_by_url: dict[str, str], title_by_url: dict[str, str]) -> None:
        self.html_by_url = html_by_url
        self.title_by_url = title_by_url
        self.closed = False

    def __enter__(self) -> "FakeContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def new_page(self) -> FakePage:
        return FakePage(self.html_by_url, self.title_by_url)

    def close(self) -> None:
        self.closed = True


class FakeBrowser:
    def __init__(self, html_by_url: dict[str, str], title_by_url: dict[str, str]) -> None:
        self.context = FakeContext(html_by_url, title_by_url)

    def new_context(self) -> FakeContext:
        return self.context


def test_download_job_html_pages_writes_html_using_raw_html_slug(
    tmp_path: Path,
) -> None:
    first_url = "https://vacancy.sioux.eu/vacancies/one.html"
    second_url = "https://vacancy.sioux.eu/vacancies/two.html"
    browser = FakeBrowser(
        {
            first_url: "<html>one</html>",
            second_url: "<html>two</html>",
        },
        {
            first_url: "Senior Software Engineer",
            second_url: "Mechatronics Architect",
        },
    )

    output_paths = download_job_html_pages(
        browser,
        [first_url, second_url],
        tmp_path,
    )

    assert output_paths == [
        tmp_path / raw_html_filename("Senior Software Engineer", first_url),
        tmp_path / raw_html_filename("Mechatronics Architect", second_url),
    ]
    assert output_paths[0].read_text(encoding="utf-8") == "<html>one</html>"
    assert output_paths[1].read_text(encoding="utf-8") == "<html>two</html>"
    assert browser.context.closed is True
