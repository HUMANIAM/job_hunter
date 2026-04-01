import pytest

from sources.registry import get_source


def test_get_source_returns_registered_sioux_source() -> None:
    source = get_source("sioux")

    assert source.company_slug == "sioux"
    assert source.source_url == "https://vacancy.sioux.eu/"
    assert source.configured_countries == ()
    assert source.configured_languages == ()


def test_get_source_raises_clear_error_for_unknown_company() -> None:
    with pytest.raises(
        ValueError,
        match="unknown company 'unknown'. Available companies: sioux",
    ):
        get_source("unknown")
