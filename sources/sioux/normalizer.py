from __future__ import annotations

from shared.normalizer import normalize_taxonomy_name


def normalize_job_tag_key(value: str) -> str:
    return normalize_taxonomy_name(value)
