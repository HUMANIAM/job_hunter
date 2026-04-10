#!/usr/bin/env python3
# pyright: reportMissingImports=false
# mypy: disable-error-code=import-not-found
from __future__ import annotations

import argparse
from typing import Sequence

if __package__ in {None, ""}:
    raise SystemExit("Run this CLI as a module: python -m clients.clients_cli ...")

from playwright.sync_api import sync_playwright

from clients.clients import Client, parse_client
from clients.registry import get_client_adapter
from infra.browser import launched_chromium


def _positive_int(value: str) -> int:
    parsed_value = int(value)
    if parsed_value < 1:
        raise argparse.ArgumentTypeError("--job-limit must be >= 1")
    return parsed_value


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect job links for a client.")
    parser.add_argument(
        "company",
        help=f"Client/company slug. Available: {', '.join(client.value for client in Client)}",
    )
    parser.add_argument(
        "--job-limit",
        type=_positive_int,
        help="Maximum number of job links to collect.",
    )
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)

    try:
        client = parse_client(args.company)
        adapter = get_client_adapter(client)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc

    with sync_playwright() as playwright:
        with launched_chromium(playwright, headless=True) as browser:
            links = adapter.collect_job_links(browser, job_limit=args.job_limit)

    for link in links:
        print(link)


if __name__ == "__main__":
    main()
