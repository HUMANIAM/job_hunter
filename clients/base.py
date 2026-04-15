from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List, Tuple


class BaseClientAdapter(ABC):
    @abstractmethod
    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int,
    ) -> List[str]:
        """Return job detail links for this client."""
        raise NotImplementedError

    def transform_downloaded_html(
        self,
        *,
        url: str,
        title: str | None,
        html_content: str,
    ) -> Tuple[str | None, str]:
        """Allow client adapters to normalize downloaded HTML before persistence."""
        return title, html_content
