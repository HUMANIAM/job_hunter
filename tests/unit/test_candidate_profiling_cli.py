from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.candidate_profiling import candidate_profiling_cli


class FakeCandidateProfile:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return self._payload


def _candidate_profile_payload() -> FakeCandidateProfile:
    return FakeCandidateProfile(
        {
            "role_titles": {
                "primary": "embedded software engineer",
                "alternatives": ["software engineer"],
                "confidence": 0.94,
                "evidence": ["Senior Embedded Software Engineer"],
            }
        }
    )


def test_parse_args_defaults_to_refactor_candidate_directories() -> None:
    args = candidate_profiling_cli.parse_args([])

    assert args.input_path == candidate_profiling_cli.DEFAULT_CANDIDATE_INPUT_PATH
    assert args.output_path == candidate_profiling_cli.DEFAULT_CANDIDATE_PROFILE_OUTPUT_PATH
    assert args.n is None


def test_parse_args_accepts_n_limit() -> None:
    args = candidate_profiling_cli.parse_args(["-n", "2"])

    assert args.n == 2


def test_run_candidate_profiling_supports_single_input_file_and_output_file(
    tmp_path: Path,
    monkeypatch,
) -> None:
    input_path = tmp_path / "candidate.md"
    input_path.write_text("# Candidate", encoding="utf-8")
    output_path = tmp_path / "candidate_profile.json"
    monkeypatch.setattr(candidate_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        candidate_profiling_cli,
        "convert_to_text",
        lambda path: f"converted::{Path(path).name}",
    )

    profile_inputs: list[str] = []

    def fake_profile_candidate_text(candidate_text: str) -> FakeCandidateProfile:
        profile_inputs.append(candidate_text)
        return _candidate_profile_payload()

    monkeypatch.setattr(
        candidate_profiling_cli,
        "profile_candidate_text",
        fake_profile_candidate_text,
    )

    result = candidate_profiling_cli.run_candidate_profiling(
        input_path=input_path,
        output_path=output_path,
    )

    assert profile_inputs == ["converted::candidate.md"]
    assert result.input_path == input_path
    assert result.output_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == (
        _candidate_profile_payload().model_dump(mode="json")
    )


def test_run_candidate_profiling_for_input_path_supports_directory_output_dir(
    tmp_path: Path,
    monkeypatch,
) -> None:
    input_dir = tmp_path / "cvs"
    input_dir.mkdir()
    first_input_path = input_dir / "a.md"
    second_input_path = input_dir / "b.txt"
    first_input_path.write_text("First Candidate", encoding="utf-8")
    second_input_path.write_text("Second Candidate", encoding="utf-8")

    output_dir = tmp_path / "profiles"
    monkeypatch.setattr(candidate_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        candidate_profiling_cli,
        "convert_to_text",
        lambda path: Path(path).read_text(encoding="utf-8"),
    )

    profile_inputs: list[str] = []

    def fake_profile_candidate_text(candidate_text: str) -> FakeCandidateProfile:
        profile_inputs.append(candidate_text)
        return _candidate_profile_payload()

    monkeypatch.setattr(
        candidate_profiling_cli,
        "profile_candidate_text",
        fake_profile_candidate_text,
    )

    results = candidate_profiling_cli.run_candidate_profiling_for_input_path(
        input_path=input_dir,
        output_path=output_dir,
    )

    assert [result.input_path for result in results] == [first_input_path, second_input_path]
    assert profile_inputs == ["First Candidate", "Second Candidate"]
    assert json.loads((output_dir / "a.json").read_text(encoding="utf-8")) == (
        _candidate_profile_payload().model_dump(mode="json")
    )
    assert json.loads((output_dir / "b.json").read_text(encoding="utf-8")) == (
        _candidate_profile_payload().model_dump(mode="json")
    )


def test_run_candidate_profiling_for_input_path_supports_n_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    input_dir = tmp_path / "cvs"
    input_dir.mkdir()
    for stem in ("a", "b", "c"):
        (input_dir / f"{stem}.md").write_text(stem, encoding="utf-8")

    output_dir = tmp_path / "profiles"
    monkeypatch.setattr(candidate_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        candidate_profiling_cli,
        "convert_to_text",
        lambda path: Path(path).read_text(encoding="utf-8"),
    )
    monkeypatch.setattr(
        candidate_profiling_cli,
        "profile_candidate_text",
        lambda _candidate_text: _candidate_profile_payload(),
    )

    results = candidate_profiling_cli.run_candidate_profiling_for_input_path(
        input_path=input_dir,
        output_path=output_dir,
        input_limit=2,
    )

    assert len(results) == 2
    assert len(list(output_dir.glob("*.json"))) == 2


def test_run_candidate_profiling_for_input_path_rejects_file_output_for_directory_input(
    tmp_path: Path,
) -> None:
    input_dir = tmp_path / "cvs"
    input_dir.mkdir()
    (input_dir / "candidate.md").write_text("candidate", encoding="utf-8")
    output_path = tmp_path / "candidate.json"

    with pytest.raises(
        SystemExit,
        match="candidate output path must be a directory when input path is a directory",
    ):
        candidate_profiling_cli.run_candidate_profiling_for_input_path(
            input_path=input_dir,
            output_path=output_path,
        )
