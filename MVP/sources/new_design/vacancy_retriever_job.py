#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    # Direct `python path/to/script.py` runs from this file's directory; add the
    # repository root so top-level packages like `MVP` and `reporting` import.
    project_root = str(Path(__file__).resolve().parents[3])
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

from MVP.clients import Client, parse_client
from MVP.sources.new_design.types import VacancyLinkRetrievalCriteria, VacancyLinks
from MVP.sources.new_design.vacancy_source_registery import (
    VacancySourceRegistry,
    create_vacancy_source_registry,
)
from reporting.writer import raw_html_filename


def _positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("--job-limit must be >= 1")
    return parsed_value


def _default_urls_path(client: Client) -> Path:
    return Path("data/MVP/jobs") / client.value / "urls.md"


def _default_html_dir(client: Client) -> Path:
    return Path("data/MVP/jobs") / client.value / "html"


def _write_links_file(output_path: Path, links: set[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(links)
    if content:
        content += "\n"
    output_path.write_text(content, encoding="utf-8")


def _get_vacancy_links(
    *,
    registry: VacancySourceRegistry,
    client: Client,
    criteria: VacancyLinkRetrievalCriteria,
) -> VacancyLinks:
    source = registry.get_vacancy_source(client)
    return source.get_vacancy_links(criteria=criteria)


def _download_and_save_vacancy_html_pages(
    *,
    registry: VacancySourceRegistry,
    client: Client,
    vacancy_links: VacancyLinks,
    html_dir: Path,
) -> None:
    html_dir.mkdir(parents=True, exist_ok=True)

    source = registry.get_vacancy_source(client)
    for vacancy_url in vacancy_links.links:
        html_content = source.get_vacancy_page(vacancy_url)
        output_path = html_dir / raw_html_filename(
            None,
            vacancy_url,
            html_content=html_content,
        )
        output_path.write_text(html_content, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect vacancy links using the new source design."
    )
    parser.add_argument(
        "company",
        help=(
            "Client/company slug. "
            f"Available: {', '.join(client.value for client in Client)}"
        ),
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of job links to collect. If omitted, retrieves all links.",
    )
    parser.add_argument(
        "--country",
        help="Country descriptor to collect. Defaults to the source default.",
    )
    parser.add_argument(
        "--urls-path",
        type=Path,
        help="Where to save retrieved vacancy URLs.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help="Download retrieved vacancy HTML pages after collecting URLs.",
    )
    parser.add_argument(
        "--html-dir",
        type=Path,
        help="Where to save downloaded vacancy HTML pages.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    # Validate client argument.
    try:
        client = parse_client(args.company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    # Prepare retrieval criteria and paths.
    criteria = VacancyLinkRetrievalCriteria(
        links_limit=args.job_limit,
        country=args.country,
    )

    urls_path = args.urls_path or _default_urls_path(client)

    with create_vacancy_source_registry() as registry:
        # Retrieve vacancy links.
        vacancy_links = _get_vacancy_links(
            registry=registry,
            client=client,
            criteria=criteria,
        )

        # Save retrieved links to file.
        _write_links_file(urls_path, vacancy_links.links)

        print("================ retrieved links ===================")
        for link in vacancy_links.links:
            print(link)

        print(f"saved links to: {urls_path}")

        # Optionally download vacancy HTML pages.
        if args.download:
            html_dir = args.html_dir or _default_html_dir(client)
            _download_and_save_vacancy_html_pages(
                registry=registry,
                client=client,
                vacancy_links=vacancy_links,
                html_dir=html_dir,
            )
            print(f"saved html to: {html_dir}")


if __name__ == "__main__":
    main()
