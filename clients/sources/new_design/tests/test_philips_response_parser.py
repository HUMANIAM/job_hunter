from __future__ import annotations

import sys

from clients.sources.new_design.philips import philips_config as config
from clients.sources.new_design.philips import philips_response_parser
from clients.sources.new_design.types import VacancyLinks


def _job_posting(path: str) -> dict[str, str]:
    return {"externalPath": path}


def test_extract_vacancy_links_respects_concrete_limit() -> None:
    links = philips_response_parser.extract_vacancy_links(
        [
            _job_posting("/job/Eindhoven/Role_1"),
            _job_posting("/job/Eindhoven/Role_2"),
            _job_posting("/job/Eindhoven/Role_3"),
        ],
        links_limit=2,
    )

    assert links == VacancyLinks(
        links={
            f"{config.ENTRY_URL}/job/Eindhoven/Role_1",
            f"{config.ENTRY_URL}/job/Eindhoven/Role_2",
        }
    )


def test_extract_vacancy_links_treats_large_limit_as_unbounded() -> None:
    links = philips_response_parser.extract_vacancy_links(
        [
            _job_posting("/job/Eindhoven/Role_1"),
            _job_posting("/not-a-job/Eindhoven/Role_2"),
            _job_posting("/job/Eindhoven/Role_3"),
        ],
        links_limit=sys.maxsize,
    )

    assert links == VacancyLinks(
        links={
            f"{config.ENTRY_URL}/job/Eindhoven/Role_1",
            f"{config.ENTRY_URL}/job/Eindhoven/Role_3",
        }
    )


def test_extract_vacancy_links_returns_empty_for_zero_limit() -> None:
    links = philips_response_parser.extract_vacancy_links(
        [_job_posting("/job/Eindhoven/Role_1")],
        links_limit=0,
    )

    assert links == VacancyLinks(links=set())
