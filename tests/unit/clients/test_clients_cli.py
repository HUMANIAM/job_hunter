from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from types import SimpleNamespace
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

from clients import clients_cli
from reporting.writer import raw_html_filename


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, int | None]] = []
        self.transform_calls: list[tuple[str, str | None, str]] = []

    def collect_job_links(
        self,
        browser: object,
        *,
        job_limit: int | None = None,
    ) -> list[str]:
        self.calls.append((browser, job_limit))
        return [
            "https://vacancy.sioux.eu/vacancies/one.html",
            "https://vacancy.sioux.eu/vacancies/two.html",
        ]

    def transform_downloaded_html(
        self,
        *,
        url: str,
        title: str | None,
        html_content: str,
    ) -> tuple[str | None, str]:
        self.transform_calls.append((url, title, html_content))
        return title, html_content


def _yield(value: object):
    @contextmanager
    def _manager():
        yield value

    return _manager()


def test_parse_args_accepts_company_and_job_limit() -> None:
    args = clients_cli.parse_args(["sioux", "--job-limit", "3"])

    assert args.company == "sioux"
    assert args.job_limit == 3
    assert args.download is False


def test_parse_args_accepts_download_flag() -> None:
    args = clients_cli.parse_args(["sioux", "--download"])

    assert args.company == "sioux"
    assert args.download is True


def test_main_collects_links_and_prints_each_one(
    monkeypatch,
    capsys,
) -> None:
    fake_adapter = FakeAdapter()
    fake_browser = object()

    monkeypatch.setattr(clients_cli, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        clients_cli,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(fake_browser),
    )
    monkeypatch.setattr(clients_cli, "get_client_adapter", lambda client: fake_adapter)
    monkeypatch.setattr(
        clients_cli,
        "download_job_html_pages",
        lambda browser, links, *, adapter=None: [],
    )

    clients_cli.main(["sioux", "--job-limit", "2"])

    assert fake_adapter.calls == [(fake_browser, 2)]
    assert capsys.readouterr().out.splitlines() == [
        "================ retrieved links ===================",
        "https://vacancy.sioux.eu/vacancies/one.html",
        "https://vacancy.sioux.eu/vacancies/two.html",
        "saved links to: data/refactor/jobs/sioux/urls.md",
    ]


def test_main_downloads_html_from_urls_file_when_flag_enabled(
    monkeypatch,
    capsys,
    tmp_path: Path,
) -> None:
    fake_adapter = FakeAdapter()
    fake_browser = object()
    download_calls: list[tuple[object, list[str]]] = []
    fake_pages = [
        SimpleNamespace(
            url="https://vacancy.sioux.eu/vacancies/one.html",
            title="Senior Software Engineer",
            html_content="<html>one</html>",
        ),
        SimpleNamespace(
            url="https://vacancy.sioux.eu/vacancies/two.html",
            title="Mechatronics Architect",
            html_content="<html>two</html>",
        ),
    ]

    monkeypatch.setattr(clients_cli, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        clients_cli,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(fake_browser),
    )
    monkeypatch.setattr(
        clients_cli,
        "download_job_html_pages",
        lambda browser, links, *, adapter=None: download_calls.append(
            (browser, list(links), adapter)
        ) or fake_pages,
    )
    monkeypatch.setattr(clients_cli, "get_client_adapter", lambda client: fake_adapter)
    monkeypatch.chdir(tmp_path)
    urls_path = tmp_path / "data" / "refactor" / "jobs" / "sioux" / "urls.md"
    urls_path.parent.mkdir(parents=True, exist_ok=True)
    urls_path.write_text(
        "\n".join(
            [
                "https://vacancy.sioux.eu/vacancies/one.html",
                "https://vacancy.sioux.eu/vacancies/two.html",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    clients_cli.main(["sioux", "--job-limit", "2", "--download"])

    assert fake_adapter.calls == []
    assert download_calls == [
        (
            fake_browser,
            [
                "https://vacancy.sioux.eu/vacancies/one.html",
                "https://vacancy.sioux.eu/vacancies/two.html",
            ],
            fake_adapter,
        )
    ]
    output_dir = tmp_path / "data" / "refactor" / "jobs" / "sioux" / "html"
    assert (
        output_dir / raw_html_filename("Senior Software Engineer", fake_pages[0].url)
    ).read_text(encoding="utf-8") == "<html>one</html>"
    assert (
        output_dir / raw_html_filename("Mechatronics Architect", fake_pages[1].url)
    ).read_text(encoding="utf-8") == "<html>two</html>"
    assert capsys.readouterr().out.splitlines() == [
        "================ retrieved links ===================",
        "https://vacancy.sioux.eu/vacancies/one.html",
        "https://vacancy.sioux.eu/vacancies/two.html",
        "loaded links from: data/refactor/jobs/sioux/urls.md",
    ]


def test_main_downloads_html_using_metadata_title_when_page_title_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_browser = object()
    fake_pages = [
        SimpleNamespace(
            url="https://example.com/jobs/software-development-engineer",
            title=None,
            html_content=(
                "<html><head>"
                '<meta property="og:title" content="Software Development Engineer - AI"/>'
                "</head><body></body></html>"
            ),
        ),
    ]

    monkeypatch.setattr(clients_cli, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        clients_cli,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(fake_browser),
    )
    monkeypatch.setattr(
        clients_cli,
        "download_job_html_pages",
        lambda browser, links, *, adapter=None: fake_pages,
    )
    monkeypatch.setattr(clients_cli, "get_client_adapter", lambda client: FakeAdapter())
    monkeypatch.chdir(tmp_path)
    urls_path = tmp_path / "data" / "refactor" / "jobs" / "sioux" / "urls.md"
    urls_path.parent.mkdir(parents=True, exist_ok=True)
    urls_path.write_text(
        "https://example.com/jobs/software-development-engineer\n",
        encoding="utf-8",
    )

    clients_cli.main(["sioux", "--download"])

    output_dir = tmp_path / "data" / "refactor" / "jobs" / "sioux" / "html"
    output_paths = list(output_dir.glob("*.html"))
    assert len(output_paths) == 1
    assert output_paths[0].name.startswith("software_development_engineer_ai__")


def test_main_download_raises_when_urls_file_is_missing(
    monkeypatch,
    tmp_path: Path,
) -> None:
    fake_browser = object()
    monkeypatch.setattr(clients_cli, "sync_playwright", lambda: _yield(object()))
    monkeypatch.setattr(
        clients_cli,
        "launched_chromium",
        lambda playwright, *, headless=True: _yield(fake_browser),
    )
    monkeypatch.setattr(clients_cli, "get_client_adapter", lambda client: FakeAdapter())
    monkeypatch.chdir(tmp_path)

    try:
        clients_cli.main(["sioux", "--download"])
    except FileNotFoundError as exc:
        assert str(exc) == "URLs file not found: data/refactor/jobs/sioux/urls.md"
    else:
        raise AssertionError("expected FileNotFoundError")
