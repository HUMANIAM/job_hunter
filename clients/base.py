from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Any, List


class BaseClientAdapter(ABC):
    @abstractmethod
    def collect_job_links(
        self,
        browser: Any,
        *,
        job_limit: int | None = None,
    ) -> List[str]:
        """Return job detail links for this client."""
        raise NotImplementedError
