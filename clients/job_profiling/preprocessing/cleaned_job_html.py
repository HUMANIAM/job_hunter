import re
from typing import List

from pydantic import BaseModel, field_validator


HTML_TAG_RE = re.compile(r"^[a-z][a-z0-9]*$")


class CleanedJobHtmlLine(BaseModel):
    html_tag: str
    text: str

    @field_validator("html_tag")
    @classmethod
    def validate_html_tag(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("html_tag is empty")
        if not HTML_TAG_RE.match(normalized):
            raise ValueError(f"invalid html tag: {value!r}")
        return normalized

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text is empty")
        if "\n" in normalized:
            raise ValueError("text must be a single line")
        return normalized


class CleanedJobHtml(BaseModel):
    lines: List[CleanedJobHtmlLine]

    @field_validator("lines")
    @classmethod
    def validate_lines(cls, value: List[CleanedJobHtmlLine]) -> List[CleanedJobHtmlLine]:
        if not value:
            raise ValueError("lines must not be empty")
        return value
