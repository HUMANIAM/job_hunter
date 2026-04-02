from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from shared.normalizer import (
    normalize_and_dedupe_texts,
    normalize_taxonomy_name,
    normalize_text,
)


def _load_sioux_normalizer():
    module_path = Path(__file__).resolve().parents[2] / "sources" / "sioux" / "normalizer.py"
    spec = importlib.util.spec_from_file_location("tests_sioux_normalizer", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


normalize_job_tag_key = _load_sioux_normalizer().normalize_job_tag_key


def test_normalize_text_collapses_internal_whitespace() -> None:
    assert normalize_text("  Senior \n\t Controls   Engineer  ") == (
        "Senior Controls Engineer"
    )


def test_normalize_taxonomy_name_lowercases_normalized_text() -> None:
    assert normalize_taxonomy_name("  IEC \n\t 61508  ") == "iec 61508"


def test_normalize_and_dedupe_texts_dedupes_case_insensitively() -> None:
    assert normalize_and_dedupe_texts(
        [" Eindhoven ", "eindhoven", "", " Hybrid  ", "hybrid"]
    ) == ["Eindhoven", "Hybrid"]


def test_normalize_job_tag_key_lowercases_normalized_text() -> None:
    assert normalize_job_tag_key("  Education   Level  ") == "education level"
