import argparse

import pytest

from shared.cli import positive_int_arg


def test_positive_int_arg_accepts_positive_value() -> None:
    parser = positive_int_arg("--count")

    assert parser("3") == 3


def test_positive_int_arg_rejects_non_positive_value() -> None:
    parser = positive_int_arg("--count")

    with pytest.raises(argparse.ArgumentTypeError, match="--count must be >= 1"):
        parser("0")
