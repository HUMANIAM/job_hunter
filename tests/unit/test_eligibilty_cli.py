from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.eligibility import eligibility_cli


class FakeEligibilityResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload
        self.decision = str(payload["decision"])

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return self._payload


def _candidate_profile_payload() -> dict[str, object]:
    return {
        "role_titles": {
            "primary": "embedded software engineer",
            "alternatives": ["software engineer"],
            "confidence": 0.94,
            "evidence": ["Senior Embedded Software Engineer"],
        }
    }


def _vacancy_profile_payload(*, primary_role: str = "embedded software engineer") -> dict[str, object]:
    return {
        "role_titles": {
            "primary": primary_role,
            "alternatives": ["software engineer"],
            "confidence": 0.94,
            "evidence": ["Senior Embedded Software Engineer"],
        }
    }


def _eligibility_response_payload() -> FakeEligibilityResponse:
    return FakeEligibilityResponse(
        {
            "eligibility_score": 0.84,
            "decision": "eligible",
            "blocker_reasons": [],
            "support_reasons": ["role fit"],
            "field_assessments": [],
        }
    )


def test_parse_args_defaults_to_refactor_candidate_directories() -> None:
    args = eligibility_cli.parse_args([])

    assert (
        args.candidate_profile_path
        == eligibility_cli.DEFAULT_CANDIDATE_PROFILE_INPUT_PATH
    )
    assert (
        args.vacancy_profile_input_path
        == eligibility_cli.DEFAULT_VACANCY_PROFILE_INPUT_PATH
    )
    assert args.output_path == eligibility_cli.DEFAULT_ELIGIBILITY_OUTPUT_PATH
    assert args.n is None


def test_parse_args_accepts_n_limit() -> None:
    args = eligibility_cli.parse_args(["-n", "2"])

    assert args.n == 2


def test_run_eligibility_supports_single_vacancy_profile(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_profile_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_profile_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )
    vacancy_profile_dir = tmp_path / "sioux" / "vacancy_profiles"
    vacancy_profile_dir.mkdir(parents=True)
    vacancy_profile_path = vacancy_profile_dir / "vacancy_embedded_software_engineer.json"
    vacancy_profile_path.write_text(
        json.dumps(_vacancy_profile_payload()),
        encoding="utf-8",
    )
    output_root = tmp_path / "eligibility"
    monkeypatch.setattr(eligibility_cli, "log", lambda _message: None)

    evaluate_calls: list[tuple[str, str]] = []

    def fake_evaluate_eligibility(candidate_profile, vacancy_profile) -> FakeEligibilityResponse:
        evaluate_calls.append(
            (
                candidate_profile.role_titles.primary,
                vacancy_profile.role_titles.primary,
            )
        )
        return _eligibility_response_payload()

    monkeypatch.setattr(
        eligibility_cli,
        "evaluate_eligibility",
        fake_evaluate_eligibility,
    )

    result = eligibility_cli.run_eligibility(
        candidate_profile_path=candidate_profile_path,
        vacancy_profile_path=vacancy_profile_path,
        output_path=output_root,
    )

    expected_output_path = (
        output_root
        / "Ibrahim_Saad_CV"
        / "eligible"
        / "sioux"
        / vacancy_profile_path.name
    )
    assert evaluate_calls == [
        ("embedded software engineer", "embedded software engineer")
    ]
    assert result.candidate_profile_path == candidate_profile_path
    assert result.vacancy_profile_path == vacancy_profile_path
    assert result.output_path == expected_output_path
    assert json.loads(expected_output_path.read_text(encoding="utf-8")) == (
        _eligibility_response_payload().model_dump(mode="json")
    )


def test_run_eligibility_for_input_path_supports_directory_output_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_profile_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_profile_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )
    vacancy_dir = tmp_path / "sioux" / "vacancy_profiles"
    vacancy_dir.mkdir(parents=True)
    first_vacancy_path = vacancy_dir / "a.json"
    second_vacancy_path = vacancy_dir / "b.json"
    first_vacancy_path.write_text(
        json.dumps(_vacancy_profile_payload(primary_role="embedded software engineer")),
        encoding="utf-8",
    )
    second_vacancy_path.write_text(
        json.dumps(_vacancy_profile_payload(primary_role="firmware engineer")),
        encoding="utf-8",
    )

    output_dir = tmp_path / "eligibility"
    monkeypatch.setattr(eligibility_cli, "log", lambda _message: None)

    evaluate_calls: list[str] = []

    def fake_evaluate_eligibility(candidate_profile, vacancy_profile) -> FakeEligibilityResponse:
        evaluate_calls.append(
            f"{candidate_profile.role_titles.primary}->{vacancy_profile.role_titles.primary}"
        )
        return _eligibility_response_payload()

    monkeypatch.setattr(
        eligibility_cli,
        "evaluate_eligibility",
        fake_evaluate_eligibility,
    )

    results = eligibility_cli.run_eligibility_for_input_path(
        candidate_profile_path=candidate_profile_path,
        vacancy_profile_input_path=vacancy_dir,
        output_path=output_dir,
    )

    candidate_output_dir = output_dir / "Ibrahim_Saad_CV" / "eligible" / "sioux"
    assert [result.vacancy_profile_path for result in results] == [
        first_vacancy_path,
        second_vacancy_path,
    ]
    assert evaluate_calls == [
        "embedded software engineer->embedded software engineer",
        "embedded software engineer->firmware engineer",
    ]
    assert json.loads((candidate_output_dir / "a.json").read_text(encoding="utf-8")) == (
        _eligibility_response_payload().model_dump(mode="json")
    )
    assert json.loads((candidate_output_dir / "b.json").read_text(encoding="utf-8")) == (
        _eligibility_response_payload().model_dump(mode="json")
    )


def test_run_eligibility_for_input_path_supports_n_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_profile_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_profile_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )
    vacancy_dir = tmp_path / "sioux" / "vacancy_profiles"
    vacancy_dir.mkdir(parents=True)
    for stem in ("a", "b", "c"):
        (vacancy_dir / f"{stem}.json").write_text(
            json.dumps(_vacancy_profile_payload(primary_role=stem)),
            encoding="utf-8",
        )

    output_dir = tmp_path / "eligibility"
    monkeypatch.setattr(eligibility_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        eligibility_cli,
        "evaluate_eligibility",
        lambda _candidate_profile, _vacancy_profile: _eligibility_response_payload(),
    )

    results = eligibility_cli.run_eligibility_for_input_path(
        candidate_profile_path=candidate_profile_path,
        vacancy_profile_input_path=vacancy_dir,
        output_path=output_dir,
        input_limit=2,
    )

    assert len(results) == 2
    assert len(
        list((output_dir / "Ibrahim_Saad_CV" / "eligible" / "sioux").glob("*.json"))
    ) == 2


def test_run_eligibility_for_input_path_rejects_file_output_path(
    tmp_path: Path,
) -> None:
    candidate_profile_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_profile_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )
    vacancy_dir = tmp_path / "sioux" / "vacancy_profiles"
    vacancy_dir.mkdir(parents=True)
    (vacancy_dir / "vacancy.json").write_text(
        json.dumps(_vacancy_profile_payload()),
        encoding="utf-8",
    )
    output_path = tmp_path / "eligibility.json"

    with pytest.raises(
        SystemExit,
        match="eligibility output path must be a directory",
    ):
        eligibility_cli.run_eligibility_for_input_path(
            candidate_profile_path=candidate_profile_path,
            vacancy_profile_input_path=vacancy_dir,
            output_path=output_path,
        )
