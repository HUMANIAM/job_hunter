import json
from pathlib import Path

from reporting import writer as output_writer


def test_sioux_output_paths_use_job_profiles_directory() -> None:
    expected_dir = Path("data/job_profiles/sioux")

    assert output_writer.OUTPUT_DIR == expected_dir
    assert output_writer.RAW_OUTPUT_DIR == expected_dir / "raw"
    assert output_writer.EVALUATED_OUTPUT_DIR == expected_dir / "evaluated"
    assert output_writer.MATCH_OUTPUT_DIR == expected_dir / "match"
    assert (
        output_writer.VALIDATION_OUTPUT_PATH
        == expected_dir / "jobs_sioux_validation.json"
    )


def test_output_paths_can_be_computed_for_other_company() -> None:
    expected_dir = Path("data/job_profiles/asml")

    assert output_writer.output_dir_for("asml") == expected_dir
    assert output_writer.raw_output_dir_for("asml") == expected_dir / "raw"
    assert output_writer.evaluated_output_dir_for("asml") == expected_dir / "evaluated"
    assert output_writer.match_output_dir_for("asml") == expected_dir / "match"
    assert (
        output_writer.validation_output_path_for("asml")
        == expected_dir / "jobs_asml_validation.json"
    )


def test_job_profile_filename_uses_slug_and_url_hash() -> None:
    filename = output_writer.job_profile_filename(
        "Senior Software Engineer C++",
        "https://example.com/jobs/cpp",
    )

    assert filename.startswith("senior_software_engineer_c__")
    assert filename.endswith(".json")


def test_write_validation_report_uses_validation_output_path(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(output_writer, "BASE_OUTPUT_DIR", tmp_path / "profiles")

    validation_report = {
        "facet_union_unique_count": 1,
        "unfiltered_pagination_unique_count": 1,
        "sets_exactly_equal": True,
    }

    output_path = output_writer.write_validation_report(validation_report)

    assert output_path == (
        tmp_path / "profiles" / "sioux" / "jobs_sioux_validation.json"
    )
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


def test_write_raw_job_writes_expected_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(output_writer, "BASE_OUTPUT_DIR", tmp_path / "profiles")

    payload = {"title": "Controls Engineer", "url": "https://example.com/controls"}
    output_path = output_writer.write_raw_job(payload)

    assert output_path.parent == tmp_path / "profiles" / "sioux" / "raw"
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload


def test_write_evaluated_job_writes_expected_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(output_writer, "BASE_OUTPUT_DIR", tmp_path / "profiles")

    payload = {
        "title": "Controls Engineer",
        "url": "https://example.com/controls",
        "decision": "keep",
    }
    output_path = output_writer.write_evaluated_job(payload)

    assert output_path.parent == tmp_path / "profiles" / "sioux" / "evaluated"
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload


def test_write_match_job_writes_expected_payload(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(output_writer, "BASE_OUTPUT_DIR", tmp_path / "profiles")

    payload = {"title": "Embedded Software Engineer", "url": "https://example.com/job"}
    output_path = output_writer.write_match_job(payload)

    assert output_path.parent == tmp_path / "profiles" / "sioux" / "match"
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload
