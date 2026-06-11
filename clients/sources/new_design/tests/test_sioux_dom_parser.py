from __future__ import annotations

from clients.sources.new_design.sioux import sioux_dom_parser
from clients.sources.new_design.sioux import sioux_config
from clients.sources.new_design.tests.data.dom import FakeDOMElement
from clients.sources.new_design.types import VacancyLinks


def test_extract_discipline_facets_reads_name_url_and_expected_count() -> None:
    facet_elements = [
        FakeDOMElement(
            attributes={"href": "/vacancies/software.html"},
            text_by_selector={
                sioux_dom_parser.SIOUX_FACET_NAME_SELECTOR: " Software ",
                sioux_dom_parser.SIOUX_FACET_COUNT_SELECTOR: " 12 ",
            },
        ),
        FakeDOMElement(
            attributes={"href": "/vacancies/mechatronics.html"},
            text_by_selector={
                sioux_dom_parser.SIOUX_FACET_NAME_SELECTOR: "Mechatronics",
                sioux_dom_parser.SIOUX_FACET_COUNT_SELECTOR: "unknown",
            },
        ),
        FakeDOMElement(
            attributes={},
            text_by_selector={
                sioux_dom_parser.SIOUX_FACET_NAME_SELECTOR: "Ignored",
                sioux_dom_parser.SIOUX_FACET_COUNT_SELECTOR: "1",
            },
        ),
    ]

    facets = sioux_dom_parser.extract_discipline_facets(
        facet_elements,
        entry_url="https://vacancy.sioux.eu/",
    )

    assert facets == [
        ("Software", "https://vacancy.sioux.eu/vacancies/software.html", 12),
        (
            "Mechatronics",
            "https://vacancy.sioux.eu/vacancies/mechatronics.html",
            sioux_dom_parser.UNKNOWN_EXPECTED_COUNT,
        ),
    ]


def test_extract_vacancy_links_reads_valid_job_hrefs() -> None:
    vacancy_elements = [
        FakeDOMElement(attributes={"href": "/vacancies/software-engineer.html"}),
        FakeDOMElement(attributes={"href": "https://example.test/not-sioux.html"}),
        FakeDOMElement(attributes={}),
        FakeDOMElement(attributes={"href": "/vacancies/system-architect.html"}),
    ]

    links = sioux_dom_parser.extract_vacancy_links(
        vacancy_elements,
        entry_url=sioux_config.SIOUX_ENTRY_URL,
        job_url_pattern=sioux_config.SIOUX_JOB_URL_RE,
        links_limit=1,
    )

    assert links == VacancyLinks(
        links={"https://vacancy.sioux.eu/vacancies/software-engineer.html"}
    )


def test_extract_next_page_url_reads_first_available_href() -> None:
    next_page_elements = [
        FakeDOMElement(attributes={}),
        FakeDOMElement(attributes={"href": "/page/2"}),
    ]

    next_page_url = sioux_dom_parser.extract_next_page_url(
        next_page_elements,
        entry_url=sioux_config.SIOUX_ENTRY_URL,
    )

    assert next_page_url == "https://vacancy.sioux.eu/page/2"
