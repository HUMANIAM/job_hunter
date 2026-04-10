from __future__ import annotations

from sources.base import SourceDefinition
from sources.sioux import SIOUX_SOURCE

SOURCE_REGISTRY: dict[str, SourceDefinition] = {
    SIOUX_SOURCE.company_slug: SIOUX_SOURCE,
}


def list_available_sources() -> tuple[str, ...]:
    return tuple(sorted(SOURCE_REGISTRY))


def get_source(company_slug: str) -> SourceDefinition:
    try:
        return SOURCE_REGISTRY[company_slug]
    except KeyError as exc:
        available_sources = ", ".join(list_available_sources())
        raise ValueError(
            f"unknown company '{company_slug}'. Available companies: {available_sources}"
        ) from exc
