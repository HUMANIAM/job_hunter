import json
from pathlib import Path

from reporting import writer as output_writer


def test_sioux_output_paths_use_analysis_directory() -> None:
    # Given: the writer's configured output location
    expected_dir = Path("data/analysis/sioux")

    # Then: all Sioux artifact paths should resolve under the analysis folder
    assert output_writer.OUTPUT_DIR == expected_dir
    assert output_writer.RAW_OUTPUT_PATH == expected_dir / "jobs_sioux_raw.json"
    assert (
        output_writer.EVALUATED_OUTPUT_PATH
        == expected_dir / "jobs_sioux_evaluated.json"
    )
    assert output_writer.OUTPUT_PATH == expected_dir / "jobs_sioux.json"
    assert (
        output_writer.VALIDATION_OUTPUT_PATH
        == expected_dir / "jobs_sioux_validation.json"
    )


def test_output_paths_can_be_computed_for_other_company() -> None:
    expected_dir = Path("data/analysis/asml")

    assert output_writer.output_dir_for("asml") == expected_dir
    assert (
        output_writer.raw_output_path_for("asml")
        == expected_dir / "jobs_asml_raw.json"
    )
    assert (
        output_writer.evaluated_output_path_for("asml")
        == expected_dir / "jobs_asml_evaluated.json"
    )
    assert (
        output_writer.kept_output_path_for("asml")
        == expected_dir / "jobs_asml.json"
    )
    assert (
        output_writer.validation_output_path_for("asml")
        == expected_dir / "jobs_asml_validation.json"
    )


def test_write_validation_report_uses_validation_output_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Given: a validation output target and validation payload
    output_path = tmp_path / "data" / "analysis" / "sioux" / "validation.json"
    monkeypatch.setattr(output_writer, "VALIDATION_OUTPUT_PATH", output_path)

    validation_report = {
        "facet_union_unique_count": 1,
        "unfiltered_pagination_unique_count": 1,
        "sets_exactly_equal": True,
    }

    # When: the validation writer persists the report
    output_writer.write_validation_report(validation_report)

    # Then: the report should be written to the validation output path
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == validation_report


def test_writer_uses_infra_json_io_for_validation_report(monkeypatch) -> None:
    captured: list[tuple[Path, dict[str, object]]] = []

    monkeypatch.setattr(
        output_writer.json_io,
        "write_json",
        lambda path, payload: captured.append((path, payload)),
    )
    validation_report = {"sets_exactly_equal": True}

    output_writer.write_validation_report(validation_report)

    assert captured == [(output_writer.VALIDATION_OUTPUT_PATH, validation_report)]


def test_writer_uses_company_specific_validation_path(monkeypatch) -> None:
    captured: list[tuple[Path, dict[str, object]]] = []

    monkeypatch.setattr(
        output_writer.json_io,
        "write_json",
        lambda path, payload: captured.append((path, payload)),
    )
    validation_report = {"sets_exactly_equal": True}

    output_writer.write_validation_report(
        validation_report,
        company_slug="asml",
    )

    assert captured == [
        (output_writer.validation_output_path_for("asml"), validation_report)
    ]


def test_write_raw_jobs_writes_expected_payload(tmp_path: Path, monkeypatch) -> None:
    # Given: a raw output target and serialized jobs
    output_path = tmp_path / "data" / "analysis" / "sioux" / "raw.json"
    monkeypatch.setattr(output_writer, "RAW_OUTPUT_PATH", output_path)

    # When: the raw writer persists the jobs
    payload = output_writer.write_raw_jobs(
        jobs=[{"title": "Controls Engineer"}],
        source="https://example.com/source",
        configured_countries=("NL",),
        configured_languages=("en",),
    )

    # Then: the file payload should match the returned payload and metadata shape
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload
    assert isinstance(payload["fetched_at_unix"], int)
    assert payload["source"] == "https://example.com/source"
    assert payload["configured_countries"] == ["NL"]
    assert payload["configured_languages"] == ["en"]
    assert payload["total_jobs"] == 1
    assert payload["jobs"] == [{"title": "Controls Engineer"}]


def test_write_evaluated_jobs_writes_expected_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Given: an evaluated output target and evaluated jobs
    output_path = tmp_path / "data" / "analysis" / "sioux" / "evaluated.json"
    monkeypatch.setattr(output_writer, "EVALUATED_OUTPUT_PATH", output_path)

    evaluated_jobs = [
        {
            "title": "Controls Engineer",
            "decision": "keep",
            "reason": "title_keep_match",
        }
    ]

    # When: the evaluated writer persists the jobs
    payload = output_writer.write_evaluated_jobs(
        jobs=evaluated_jobs,
        source="https://example.com/source",
        configured_countries=(),
        configured_languages=("en",),
    )

    # Then: the evaluated payload should be written with the expected shape
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload
    assert payload["total_jobs"] == 1
    assert payload["jobs"] == evaluated_jobs


def test_write_kept_jobs_includes_relevant_job_count(
    tmp_path: Path,
    monkeypatch,
) -> None:
    # Given: a kept output target and a smaller relevant subset
    output_path = tmp_path / "data" / "analysis" / "sioux" / "kept.json"
    monkeypatch.setattr(output_writer, "OUTPUT_PATH", output_path)

    # When: the kept writer persists the relevant jobs summary
    payload = output_writer.write_kept_jobs(
        jobs=[{"title": "Embedded Software Engineer"}],
        total_jobs=4,
        source="https://example.com/source",
        configured_countries=(),
        configured_languages=("en", "nl"),
    )

    # Then: the kept payload should preserve both total and relevant job counts
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload
    assert payload["total_jobs"] == 4
    assert payload["relevant_jobs"] == 1
    assert payload["jobs"] == [{"title": "Embedded Software Engineer"}]
