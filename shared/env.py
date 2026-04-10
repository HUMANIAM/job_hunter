from __future__ import annotations

import os


def require_env_value(name: str, *, error_context: str) -> str:
    value = os.environ.get(name)
    if value:
        return value

    raise RuntimeError(f"{name} is required for {error_context}")
