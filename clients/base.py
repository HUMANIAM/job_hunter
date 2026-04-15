from __future__ import annotations
from abc import ABC
from typing import Any, List, Tuple


class BaseClientAdapter(ABC):
    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        """Return job detail links for this client."""
        with browser.new_context() as context:
            return self._collect_job_links_in_context(
                context,
                job_limit=job_limit,
            )

    def _collect_job_links_in_context(
        self,
        context: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _collect_job_links_in_context"
        )

    def transform_downloaded_html(
        self,
        *,
        url: str,
        title: str | None,
        html_content: str,
    ) -> Tuple[str | None, str]:
        """Allow client adapters to normalize downloaded HTML before persistence."""
        return title, html_content
