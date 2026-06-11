from __future__ import annotations

from dataclasses import dataclass


@dataclass
class VacancyLinks:
    links: set[str]


@dataclass(frozen=True)
class VacancyLinkRetrievalCriteria:
    links_limit: int | None = None
    country: str | None = None
