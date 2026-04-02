from __future__ import annotations

from typing import Any, Callable

from sources.base import SourceDefinition, SourceRetrievalResult
from sources.sioux import adapter as sioux_adapter
from sources.sioux import parser as sioux_parser


class SiouxSourceAdapter:
    def retrieve_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> SourceRetrievalResult:
        retrieval = sioux_adapter.retrieve_sioux_job_links(
            browser,
            job_limit=job_limit,
        )
        return SourceRetrievalResult(
            job_links=retrieval.job_links,
            discipline_map=retrieval.discipline_map,
            validation_report=retrieval.validation_report,
        )

    def log_validation_report(self, report: dict[str, Any]) -> None:
        sioux_adapter.log_collection_validation_report(report)


class SiouxSourceParser:
    def fetch_job(
        self,
        page: Any,
        url: str,
        disciplines: list[str] | None = None,
        log_message: Callable[[str], None] | None = None,
    ) -> Any:
        return sioux_parser.fetch_job(page, url, disciplines, log_message)


SIOUX_SOURCE = SourceDefinition(
    company_slug="sioux",
    source_url=sioux_adapter.START_URL,
    configured_countries=sioux_adapter.TARGET_COUNTRIES,
    configured_languages=sioux_adapter.TARGET_LANGUAGES,
    adapter=SiouxSourceAdapter(),
    parser=SiouxSourceParser(),
)
