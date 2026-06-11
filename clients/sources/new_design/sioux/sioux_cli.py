#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit(
        "Run this CLI as a module: "
        "python -m clients.sources.new_design.sioux.sioux_cli ..."
    )

from clients.clients import Client
from clients.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from clients.sources.new_design.vacancy_source_registery import (
    create_vacancy_source_registry,
)


DEFAULT_URLS_PATH = Path("data/refactor/jobs/sioux/urls.md")


def _positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("--job-limit must be >= 1")
    return parsed_value


def _write_links_file(output_path: Path, links: set[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(links)
    if content:
        content += "\n"
    output_path.write_text(content, encoding="utf-8")


def _get_vacancy_links(criteria: VacancyLinkRetrievalCriteria) -> VacancyLinks:
    with create_vacancy_source_registry() as registry:
        source = registry.get_vacancy_source(Client.SIOUX)
        return source.get_vacancy_links(criteria=criteria)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect Sioux vacancy links using the new source design."
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of job links to collect. If omitted, retrieves all links.",
    )
    parser.add_argument(
        "--country",
        help="Country descriptor to collect. Currently reserved for Sioux filtering.",
    )
    parser.add_argument(
        "--urls-path",
        type=Path,
        default=DEFAULT_URLS_PATH,
        help="Where to save retrieved vacancy URLs.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    criteria = VacancyLinkRetrievalCriteria(
        links_limit=args.job_limit,
        country=args.country,
    )

    vacancy_links = _get_vacancy_links(criteria)
    _write_links_file(args.urls_path, vacancy_links.links)

    print("================ retrieved links ===================")
    for link in vacancy_links.links:
        print(link)
    print(f"saved links to: {args.urls_path}")


if __name__ == "__main__":
    main()
