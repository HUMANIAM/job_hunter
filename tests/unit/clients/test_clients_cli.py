from __future__ import annotations

from contextlib import contextmanager
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


class FakeAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[object, int | None]] = []

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


def _yield(value: object):
    @contextmanager
    def _manager():
        yield value

    return _manager()


def test_parse_args_accepts_company_and_job_limit() -> None:
    args = clients_cli.parse_args(["sioux", "--job-limit", "3"])

    assert args.company == "sioux"
    assert args.job_limit == 3


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

    clients_cli.main(["sioux", "--job-limit", "2"])

    assert fake_adapter.calls == [(fake_browser, 2)]
    assert capsys.readouterr().out.splitlines() == [
        "================ retrieved links ===================",
        "https://vacancy.sioux.eu/vacancies/one.html",
        "https://vacancy.sioux.eu/vacancies/two.html",
    ]
