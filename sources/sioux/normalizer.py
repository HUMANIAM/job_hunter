from __future__ import annotations

from shared.normalizer import normalize_text


def normalize_job_tag_key(value: str) -> str:
    return normalize_text(value).lower()
