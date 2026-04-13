from __future__ import annotations

import re
from typing import Callable, Iterable, TypeVar

ItemT = TypeVar("ItemT")


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def normalize_taxonomy_name(value: str) -> str:
    return normalize_text(value).lower()


def dedupe_by_normalized_key(
    values: Iterable[ItemT],
    *,
    key_selector: Callable[[ItemT], str],
) -> list[ItemT]:
    """Return the first item for each normalized key, preserving input order.

    The selected key is normalized with ``normalize_text`` and deduped
    case-insensitively. Items whose selected key normalizes to an empty string
    are skipped.
    """
    cleaned_values: list[ItemT] = []
    seen_values: set[str] = set()

    for value in values:
        normalized = normalize_text(key_selector(value))
        if not normalized:
            continue

        dedupe_key = normalized.casefold()
        if dedupe_key in seen_values:
            continue

        cleaned_values.append(value)
        seen_values.add(dedupe_key)

    return cleaned_values


def normalize_and_dedupe_texts(values: Iterable[str]) -> list[str]:
    deduped_values = dedupe_by_normalized_key(
        values,
        key_selector=normalize_text,
    )

    return [normalize_text(value) for value in deduped_values]
