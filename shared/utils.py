from __future__ import annotations


def _max(value1: int | None, value2: int | None) -> int | None:
    if value1 is None:
        return value2

    if value2 is None:
        return value1

    return max(value1, value2)
