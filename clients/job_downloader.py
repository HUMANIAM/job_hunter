from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from infra.browser import capture_page_html, capture_page_title, open_page


@dataclass(frozen=True)
class Page:
    url: str
    title: str | None
    html_content: str


def download_job_html_pages(
    browser: Any,
    job_links: Sequence[str],
) -> list[Page]:
    pages: list[Page] = []

    with browser.new_context() as context:
        page = context.new_page()
        for link in job_links:
            open_page(page, link)
            html_content = capture_page_html(page)
            if html_content is None:
                raise RuntimeError(f"Failed to capture HTML for {link}")

            pages.append(
                Page(
                    url=link,
                    title=capture_page_title(page),
                    html_content=html_content,
                )
            )

    return pages
