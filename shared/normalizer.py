from __future__ import annotations

import re
from typing import Iterable


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_taxonomy_name(value: str) -> str:
    return normalize_text(value).lower()


def normalize_and_dedupe_texts(values: Iterable[str]) -> list[str]:
    cleaned_values: list[str] = []
    seen_values: set[str] = set()

    for value in values:
        normalized = normalize_text(value)
        if not normalized:
            continue

        key = normalized.casefold()
        if key in seen_values:
            continue

        cleaned_values.append(normalized)
        seen_values.add(key)

    return cleaned_values
