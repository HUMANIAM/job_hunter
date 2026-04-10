from __future__ import annotations

import argparse
from typing import Callable


def positive_int_arg(option_name: str) -> Callable[[str], int]:
    def parse_positive_int(value: str) -> int:
        parsed_value = int(value)
        if parsed_value < 1:
            raise argparse.ArgumentTypeError(f"{option_name} must be >= 1")
        return parsed_value

    return parse_positive_int


__all__ = ["positive_int_arg"]
