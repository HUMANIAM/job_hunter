from __future__ import annotations

from collections.abc import Sequence
from typing import Pattern, Tuple
from urllib.parse import urljoin

from clients.sources.new_design.browser_access import DOMElement
from clients.sources.new_design.types import VacancyLinks
from shared.normalizer import normalize_text


SIOUX_FACET_NAME_SELECTOR = ".filter-item-link-name"
SIOUX_FACET_COUNT_SELECTOR = ".filter-item-link-count"
UNKNOWN_EXPECTED_COUNT = -1

DisciplineFacet = Tuple[str, str, int]


def extract_discipline_facets(
    facet_elements: Sequence[DOMElement],
    *,
    entry_url: str,
) -> list[DisciplineFacet]:
    facets: list[DisciplineFacet] = []

    for element in facet_elements:
        href = element.get_attribute("href")
        if not href:
            continue

        name = normalize_text(element.get_text(SIOUX_FACET_NAME_SELECTOR))
        count_text = normalize_text(element.get_text(SIOUX_FACET_COUNT_SELECTOR))
        expected_count = (
            int(count_text) if count_text.isdigit() else UNKNOWN_EXPECTED_COUNT
        )

        facets.append((name, urljoin(entry_url, href), expected_count))

    return facets


def extract_vacancy_links(
    vacancy_elements: Sequence[DOMElement],
    *,
    entry_url: str,
    job_url_pattern: Pattern[str],
    links_limit: int,
) -> VacancyLinks:
    links: set[str] = set()

    if links_limit <= 0:
        return VacancyLinks(links=links)

    for element in vacancy_elements:
        href = element.get_attribute("href")
        if not href:
            continue

        full_url = urljoin(entry_url, href)
        if not job_url_pattern.match(full_url):
            continue

        links.add(full_url)
        if len(links) >= links_limit:
            break

    return VacancyLinks(links=links)


def extract_next_page_url(
    next_page_elements: Sequence[DOMElement],
    *,
    entry_url: str,
) -> str | None:
    for element in next_page_elements:
        href = element.get_attribute("href")
        if href:
            return urljoin(entry_url, href)

    return None
