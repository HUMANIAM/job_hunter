from shared.normalizer import normalize_text
from sources.sioux.normalizer import normalize_job_tag_key


def test_normalize_text_collapses_internal_whitespace() -> None:
    assert normalize_text("  Senior \n\t Controls   Engineer  ") == (
        "Senior Controls Engineer"
    )


def test_normalize_job_tag_key_lowercases_normalized_text() -> None:
    assert normalize_job_tag_key("  Education   Level  ") == "education level"
