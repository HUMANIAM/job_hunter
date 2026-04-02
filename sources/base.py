from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass
class SourceRetrievalResult:
    job_links: list[str]
    discipline_map: dict[str, list[str]]
    validation_report: dict[str, Any]


class SourceAdapter(Protocol):
    def retrieve_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> SourceRetrievalResult:
        ...

    def log_validation_report(self, report: dict[str, Any]) -> None:
        ...


class SourceParser(Protocol):
    def fetch_job(
        self,
        page: Any,
        url: str,
        disciplines: list[str] | None = None,
        log_message: Callable[[str], None] | None = None,
    ) -> Any:
        ...


@dataclass(frozen=True)
class SourceDefinition:
    company_slug: str
    source_url: str
    configured_countries: tuple[str, ...]
    configured_languages: tuple[str, ...]
    adapter: SourceAdapter
    parser: SourceParser
