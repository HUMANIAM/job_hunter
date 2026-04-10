from typing import Dict

import pytest
from pydantic import ValidationError

from clients.job_profiling.preprocessing.cleaned_job_html import (
    CleanedJobHtml,
    CleanedJobHtmlLine,
)


def test_cleaned_job_html_line_normalizes_fields() -> None:
    line = CleanedJobHtmlLine(
        html_tag=" H2 ",
        text=" Example text ",
    )

    assert line.html_tag == "h2"
    assert line.text == "Example text"


@pytest.mark.parametrize(
    ("payload", "error_message"),
    [
        ({"html_tag": "div-1", "text": "Example"}, "invalid html tag"),
        ({"html_tag": "div", "text": "   "}, "text is empty"),
        ({"html_tag": "div", "text": "Example\ntext"}, "text must be a single line"),
    ],
)
def test_cleaned_job_html_line_rejects_invalid_values(
    payload: Dict[str, str], error_message: str
) -> None:
    with pytest.raises(ValidationError, match=error_message):
        CleanedJobHtmlLine(**payload)


def test_cleaned_job_html_requires_non_empty_lines() -> None:
    with pytest.raises(ValidationError, match="lines must not be empty"):
        CleanedJobHtml(lines=[])
