import pytest

from sources.registry import get_source


def test_get_source_returns_registered_sioux_source() -> None:
    source = get_source("sioux")

    assert source.company_slug == "sioux"
    assert source.source_url == "https://vacancy.sioux.eu/"
    assert source.configured_countries == ()
    assert source.configured_languages == ()


def test_get_source_returns_registered_thermofisher_source() -> None:
    source = get_source("thermofisher")

    assert source.company_slug == "thermofisher"
    assert (
        source.source_url
        == "https://jobs.thermofisher.com/global/en/netherlands-jobs"
    )
    assert source.configured_countries == ("Netherlands",)
    assert source.configured_languages == ()


def test_get_source_raises_clear_error_for_unknown_company() -> None:
    with pytest.raises(
        ValueError,
        match="unknown company 'unknown'. Available companies: sioux, thermofisher",
    ):
        get_source("unknown")
