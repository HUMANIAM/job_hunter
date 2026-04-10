from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from infra.browser import capture_page_html, capture_page_title, open_page
from reporting.writer import raw_html_filename


def download_job_html_pages(
    browser: Any,
    job_links: Sequence[str],
    destination_dir: Path | str,
) -> list[Path]:
    output_dir = Path(destination_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    output_paths: list[Path] = []

    with browser.new_context() as context:
        page = context.new_page()
        for link in job_links:
            open_page(page, link)
            html_content = capture_page_html(page)
            if html_content is None:
                raise RuntimeError(f"Failed to capture HTML for {link}")

            page_title = capture_page_title(page)
            output_path = output_dir / raw_html_filename(page_title, link)
            output_path.write_text(html_content, encoding="utf-8")
            output_paths.append(output_path)

    return output_paths
