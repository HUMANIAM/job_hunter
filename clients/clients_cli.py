#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit("Run this CLI as a module: python -m clients.clients_cli ...")

from clients.job_downloader import download_job_html_pages
from playwright.sync_api import sync_playwright

from clients.clients import Client, parse_client
from clients.registry import get_client_adapter
from infra.browser import launched_chromium
from reporting.writer import raw_html_filename


def _positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("--job-limit must be >= 1")
    return parsed_value


def _default_urls_path(client: Client) -> Path:
    return Path("data/refactor/jobs") / client.value / "urls.md"


def _write_links_file(output_path: Path, links: Sequence[str]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(links)
    if content:
        content += "\n"
    output_path.write_text(content, encoding="utf-8")


def _read_links_file(input_path: Path) -> list[str]:
    if not input_path.exists():
        raise FileNotFoundError(f"URLs file not found: {input_path}")

    return [
        line.strip()
        for line in input_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect job links for a client.")
    parser.add_argument(
        "company",
        help=f"Client/company slug. Available: {', '.join(client.value for client in Client)}",
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of job links to collect or download.",
    )
    parser.add_argument(
        "--download",
        action="store_true",
        help=(
            "Download HTML pages to data/refactor/jobs/{company}/html using the "
            "links listed in --urls-path."
        ),
    )
    parser.add_argument(
        "--urls-path",
        help=(
            "Where to save retrieved vacancy URLs. "
            "Defaults to data/refactor/jobs/{company}/urls.md."
        ),
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        client = parse_client(args.company)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    urls_path = Path(args.urls_path) if args.urls_path else _default_urls_path(client)

    if args.download:
        links = _read_links_file(urls_path)
        if args.job_limit is not None:
            links = links[: args.job_limit]

        with sync_playwright() as playwright:
            with launched_chromium(playwright, headless=True) as browser:
                pages = download_job_html_pages(
                    browser,
                    links,
                )
                output_dir = Path("data/refactor/jobs") / client.value / "html"
                output_dir.mkdir(parents=True, exist_ok=True)
                for page in pages:
                    output_path = output_dir / raw_html_filename(
                        page.title,
                        page.url,
                        html_content=page.html_content,
                    )
                    output_path.write_text(page.html_content, encoding="utf-8")
    else:
        try:
            adapter = get_client_adapter(client)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc

        with sync_playwright() as playwright:
            with launched_chromium(playwright, headless=True) as browser:
                links = adapter.collect_job_links(browser, job_limit=args.job_limit)

        _write_links_file(urls_path, links)

    print("================ retrieved links ===================")
    for link in links:
        print(link)
    if args.download:
        print(f"loaded links from: {urls_path}")
    else:
        print(f"saved links to: {urls_path}")


if __name__ == "__main__":
    main()
