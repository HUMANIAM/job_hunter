import json
from pathlib import Path

from reporting import writer as output_writer


def test_sioux_output_paths_use_job_profiles_directory() -> None:
    expected_dir = Path("data/job_profiles/sioux")

    assert output_writer.OUTPUT_DIR == expected_dir
    assert output_writer.job_profile_output_path_for(
        "sioux",
        "Controls Engineer",
        "https://example.com/controls",
    ).parent == expected_dir / "evaluated"
    assert output_writer.RAW_OUTPUT_DIR == expected_dir / "raw"
    assert output_writer.EVALUATED_OUTPUT_DIR == expected_dir / "evaluated"
    assert output_writer.MATCH_OUTPUT_DIR == expected_dir / "match"
    assert output_writer.RANKING_OUTPUT_DIR == Path("data/rankings")
    assert output_writer.CANDIDATE_PROFILE_OUTPUT_DIR == Path("data/candidate_profiles")
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


def test_ranking_result_filename_uses_candidate_and_job_ids() -> None:
    filename = output_writer.ranking_result_filename(
        "Ibrahim_Saad_CV",
        "embedded_software_engineer__12345abcde",
    )

    assert filename == "Ibrahim_Saad_CV_embedded_software_engineer__12345abcde.json"


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


def test_write_job_profile_writes_expected_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(output_writer, "BASE_OUTPUT_DIR", tmp_path / "profiles")

    payload = {"title": "Controls Engineer", "url": "https://example.com/controls"}
    output_path = output_writer.write_job_profile(payload)

    assert output_path.parent == tmp_path / "profiles" / "sioux" / "evaluated"
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


def test_write_ranking_result_writes_expected_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(output_writer, "BASE_RANKING_OUTPUT_DIR", tmp_path / "rankings")

    payload = {
        "candidate_id": "Ibrahim_Saad_CV",
        "job_id": "embedded_software_engineer__12345abcde",
        "score": 0.84,
        "bucket_scores": {
            "skills": 0.9,
            "languages": 0.8,
            "protocols": 0.7,
            "standards": 0.6,
            "domains": 0.5,
            "seniority": 1.0,
            "years_experience": 0.9,
        },
        "matched_features": [],
        "missing_features": [],
    }
    output_path = output_writer.write_ranking_result(payload)

    assert output_path == (
        tmp_path
        / "rankings"
        / "Ibrahim_Saad_CV_embedded_software_engineer__12345abcde.json"
    )
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload


def test_write_candidate_profile_writes_expected_payload(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        output_writer,
        "BASE_CANDIDATE_PROFILE_DIR",
        tmp_path / "candidate_profiles",
    )

    payload = {
        "candidate_id": "Ibrahim_Saad_CV",
        "source_text_hash": "3a01ac116f682c78fdd0704ed2774349959633d1a81647b79ecd1c396f6443d1",
        "schema_version": "2.0.0",
        "profile": {
            "skills": [],
            "languages": [],
            "protocols": [],
            "standards": [],
            "domains": [],
            "seniority": {"value": None, "confidence": 0.0, "evidence": []},
            "years_experience_total": {
                "value": None,
                "confidence": 0.0,
                "evidence": [],
            },
            "candidate_constraints": {
                "preferred_locations": [],
                "excluded_locations": [],
                "preferred_workplace_types": [],
                "excluded_workplace_types": [],
                "requires_visa_sponsorship": None,
                "avoid_export_control_roles": None,
                "notes": [],
                "confidence": 0.0,
                "evidence": [],
            },
        },
    }

    output_path = output_writer.write_candidate_profile(payload)

    assert output_path == tmp_path / "candidate_profiles" / "Ibrahim_Saad_CV.json"
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == payload
