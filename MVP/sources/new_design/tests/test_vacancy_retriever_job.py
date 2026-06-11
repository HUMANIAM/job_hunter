from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from MVP.clients import Client
from MVP.sources.new_design import vacancy_retriever_job
from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from MVP.sources.new_design.vacancy_source import VacancySource
from reporting.writer import raw_html_filename


class FakeVacancySource(VacancySource):
    def __init__(self) -> None:
        self.requested_pages: list[str] = []
        self.requested_criteria: list[VacancyLinkRetrievalCriteria | None] = []

    def get_vacancy_links(
        self,
        *,
        criteria: VacancyLinkRetrievalCriteria | None = None,
    ) -> VacancyLinks:
        self.requested_criteria.append(criteria)
        links = [
            "https://example.test/jobs/one",
            "https://example.test/jobs/two",
        ]
        if criteria is not None and criteria.links_limit is not None:
            links = links[: criteria.links_limit]

        return VacancyLinks(links=set(links))

    def get_vacancy_page(self, vacancy_url: str) -> str:
        self.requested_pages.append(vacancy_url)
        return f"<html><head><title>{vacancy_url}</title></head></html>"


class FakeVacancySourceRegistry:
    def __init__(self, source: VacancySource) -> None:
        self._source = source
        self.requested_clients: list[Client] = []

    def get_vacancy_source(self, client: Client) -> VacancySource:
        self.requested_clients.append(client)
        return self._source


def test_main_downloads_vacancy_pages_to_default_mvp_html_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = FakeVacancySource()
    registry = FakeVacancySourceRegistry(source)
    create_registry_calls = 0

    @contextmanager
    def create_registry() -> Iterator[FakeVacancySourceRegistry]:
        nonlocal create_registry_calls
        create_registry_calls += 1
        yield registry

    monkeypatch.setattr(
        vacancy_retriever_job,
        "create_vacancy_source_registry",
        create_registry,
    )
    monkeypatch.chdir(tmp_path)

    vacancy_retriever_job.main(["philips", "--download", "--job-limit", "1"])

    vacancy_url = "https://example.test/jobs/one"
    html_content = f"<html><head><title>{vacancy_url}</title></head></html>"
    output_path = (
        tmp_path
        / "data"
        / "MVP"
        / "jobs"
        / "philips"
        / "html"
        / raw_html_filename(None, vacancy_url, html_content=html_content)
    )
    urls_path = tmp_path / "data" / "MVP" / "jobs" / "philips" / "urls.md"
    assert urls_path.read_text(encoding="utf-8").splitlines() == [vacancy_url]
    assert output_path.read_text(encoding="utf-8") == html_content
    assert registry.requested_clients == [Client.PHILIPS, Client.PHILIPS]
    assert source.requested_pages == [vacancy_url]
    assert len(source.requested_criteria) == 1
    assert source.requested_criteria[0] is not None
    assert source.requested_criteria[0].links_limit == 1
    assert create_registry_calls == 1


def test_main_collects_links_with_one_registry_lifecycle(
    monkeypatch,
    tmp_path: Path,
) -> None:
    source = FakeVacancySource()
    registry = FakeVacancySourceRegistry(source)
    create_registry_calls = 0

    @contextmanager
    def create_registry() -> Iterator[FakeVacancySourceRegistry]:
        nonlocal create_registry_calls
        create_registry_calls += 1
        yield registry

    monkeypatch.setattr(
        vacancy_retriever_job,
        "create_vacancy_source_registry",
        create_registry,
    )
    monkeypatch.chdir(tmp_path)

    vacancy_retriever_job.main(["philips", "--job-limit", "2"])

    urls_path = tmp_path / "data" / "MVP" / "jobs" / "philips" / "urls.md"
    assert set(urls_path.read_text(encoding="utf-8").splitlines()) == {
        "https://example.test/jobs/one",
        "https://example.test/jobs/two",
    }
    assert registry.requested_clients == [Client.PHILIPS]
    assert len(source.requested_criteria) == 1
    assert source.requested_criteria[0] is not None
    assert source.requested_criteria[0].links_limit == 2
    assert create_registry_calls == 1
