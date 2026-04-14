from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.job_profiling import job_profiling_cli


class FakeVacancyProfile:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        assert mode == "json"
        return self._payload


def _vacancy_profile_payload() -> FakeVacancyProfile:
    return FakeVacancyProfile(
        {
            "role_titles": {
                "primary": "mechatronics technician",
                "alternatives": [
                    "prototype technician",
                    "service technician",
                ],
                "confidence": 0.96,
                "evidence": [
                    "h1: Mechatronics Technician",
                    "h2: As a Mechatronics Technician, you are responsible",
                ],
            }
        }
    )


def test_parse_args_defaults_to_sioux_directories() -> None:
    args = job_profiling_cli.parse_args(["--pipeline", "pre"])

    assert args.input_path == job_profiling_cli.DEFAULT_HTML_INPUT_DIR
    assert args.pre_output_dir == job_profiling_cli.DEFAULT_PREPROCESSING_OUTPUT_DIR
    assert args.ext_output_dir == job_profiling_cli.DEFAULT_VACANCY_PROFILE_OUTPUT_DIR
    assert args.pipeline == ["pre"]
    assert args.n is None


def test_parse_args_requires_pipeline() -> None:
    with pytest.raises(SystemExit):
        job_profiling_cli.parse_args([])


def test_parse_args_defaults_ext_input_to_preprocessing_dir() -> None:
    args = job_profiling_cli.parse_args(["--pipeline", "ext"])

    assert args.input_path == job_profiling_cli.DEFAULT_PREPROCESSING_OUTPUT_DIR
    assert args.ext_output_dir == job_profiling_cli.DEFAULT_VACANCY_PROFILE_OUTPUT_DIR
    assert args.pipeline == ["ext"]


def test_parse_args_accepts_n_limit() -> None:
    args = job_profiling_cli.parse_args(["--pipeline", "pre", "-n", "3"])

    assert args.n == 3


def test_run_job_profiling_supports_pre_and_ext_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_path = tmp_path / "vacancy.html"
    html_path.write_text("<h1>Mechatronics Technician</h1>", encoding="utf-8")

    preprocessing_dir = tmp_path / "preprocessing"
    vacancy_profiles_dir = tmp_path / "vacancy_profiles"
    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        job_profiling_cli,
        "preprocess_job_html",
        lambda _raw_html: "h1: Mechatronics Technician",
    )

    profile_inputs: list[str] = []

    def fake_profile_vacancy_text(cleaned_text: str) -> FakeVacancyProfile:
        profile_inputs.append(cleaned_text)
        return _vacancy_profile_payload()

    monkeypatch.setattr(
        job_profiling_cli,
        "profile_vacancy_text",
        fake_profile_vacancy_text,
    )

    result = job_profiling_cli.run_job_profiling(
        html_path=html_path,
        pipeline=["pre", "ext"],
        preprocessing_output_dir=preprocessing_dir,
        vacancy_profile_output_dir=vacancy_profiles_dir,
    )

    preprocessing_output_path = preprocessing_dir / "vacancy.txt"
    vacancy_profile_output_path = vacancy_profiles_dir / "vacancy.json"

    assert preprocessing_output_path.read_text(encoding="utf-8") == (
        "h1: Mechatronics Technician"
    )
    assert profile_inputs == ["h1: Mechatronics Technician"]
    assert json.loads(vacancy_profile_output_path.read_text(encoding="utf-8")) == (
        _vacancy_profile_payload().model_dump(mode="json")
    )
    assert result.input_path == html_path
    assert result.phase_output_paths == {
        "pre": preprocessing_output_path,
        "ext": vacancy_profile_output_path,
    }


def test_run_job_profiling_ext_requires_preprocessed_text(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_path = tmp_path / "vacancy.html"
    html_path.write_text("<h1>Mechatronics Technician</h1>", encoding="utf-8")

    with pytest.raises(SystemExit, match="preprocessed vacancy text does not exist"):
        job_profiling_cli.run_job_profiling(
            html_path=html_path,
            pipeline=["ext"],
            preprocessing_output_dir=tmp_path / "missing-preprocessing",
        )


def test_run_job_profiling_for_input_path_rejects_ext_html_input(
    tmp_path: Path,
) -> None:
    html_path = tmp_path / "vacancy.html"
    html_path.write_text("<h1>Mechatronics Technician</h1>", encoding="utf-8")

    with pytest.raises(SystemExit, match="ext input path must point to a .txt file"):
        job_profiling_cli.run_job_profiling_for_input_path(
            input_path=html_path,
            pipeline=["ext"],
        )


def test_run_job_profiling_for_input_path_supports_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    first_html_path = html_dir / "a_vacancy.html"
    second_html_path = html_dir / "b_vacancy.html"
    first_html_path.write_text("<h1>First Vacancy</h1>", encoding="utf-8")
    second_html_path.write_text("<h1>Second Vacancy</h1>", encoding="utf-8")

    preprocessing_dir = tmp_path / "preprocessing"
    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        job_profiling_cli,
        "preprocess_job_html",
        lambda raw_html: raw_html.replace("<h1>", "").replace("</h1>", "").strip(),
    )

    results = job_profiling_cli.run_job_profiling_for_input_path(
        input_path=html_dir,
        pipeline=["pre"],
        preprocessing_output_dir=preprocessing_dir,
    )

    assert [result.input_path for result in results] == [first_html_path, second_html_path]
    assert (preprocessing_dir / "a_vacancy.txt").read_text(encoding="utf-8") == (
        "First Vacancy"
    )
    assert (preprocessing_dir / "b_vacancy.txt").read_text(encoding="utf-8") == (
        "Second Vacancy"
    )


def test_run_job_profiling_for_input_path_supports_n_limit(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    html_paths = []
    for stem in ("a_vacancy", "b_vacancy", "c_vacancy"):
        html_path = html_dir / f"{stem}.html"
        html_path.write_text(f"<h1>{stem}</h1>", encoding="utf-8")
        html_paths.append(html_path)

    preprocessing_dir = tmp_path / "preprocessing"
    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)
    monkeypatch.setattr(
        job_profiling_cli,
        "preprocess_job_html",
        lambda raw_html: raw_html.replace("<h1>", "").replace("</h1>", "").strip(),
    )

    results = job_profiling_cli.run_job_profiling_for_input_path(
        input_path=html_dir,
        pipeline=["pre"],
        input_limit=2,
        preprocessing_output_dir=preprocessing_dir,
    )

    output_paths = sorted(preprocessing_dir.glob("*.txt"))

    assert len(results) == 2
    assert len(output_paths) == 2
    assert {result.input_path for result in results}.issubset(set(html_paths))


def test_run_job_profiling_for_input_path_supports_ext_txt_directory(
    tmp_path: Path,
    monkeypatch,
) -> None:
    preprocessing_dir = tmp_path / "preprocessing"
    preprocessing_dir.mkdir()
    first_txt_path = preprocessing_dir / "a_vacancy.txt"
    second_txt_path = preprocessing_dir / "b_vacancy.txt"
    first_txt_path.write_text("First Vacancy", encoding="utf-8")
    second_txt_path.write_text("Second Vacancy", encoding="utf-8")

    vacancy_profiles_dir = tmp_path / "vacancy_profiles"
    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)

    profile_inputs: list[str] = []

    def fake_profile_vacancy_text(cleaned_text: str) -> FakeVacancyProfile:
        profile_inputs.append(cleaned_text)
        return _vacancy_profile_payload()

    monkeypatch.setattr(
        job_profiling_cli,
        "profile_vacancy_text",
        fake_profile_vacancy_text,
    )

    results = job_profiling_cli.run_job_profiling_for_input_path(
        input_path=preprocessing_dir,
        pipeline=["ext"],
        vacancy_profile_output_dir=vacancy_profiles_dir,
    )

    assert [result.input_path for result in results] == [first_txt_path, second_txt_path]
    assert profile_inputs == ["First Vacancy", "Second Vacancy"]
    assert json.loads((vacancy_profiles_dir / "a_vacancy.json").read_text(encoding="utf-8")) == (
        _vacancy_profile_payload().model_dump(mode="json")
    )
    assert json.loads((vacancy_profiles_dir / "b_vacancy.json").read_text(encoding="utf-8")) == (
        _vacancy_profile_payload().model_dump(mode="json")
    )


def test_run_job_profiling_for_input_path_skips_existing_pre_outputs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    first_html_path = html_dir / "a_vacancy.html"
    second_html_path = html_dir / "b_vacancy.html"
    first_html_path.write_text("<h1>First Vacancy</h1>", encoding="utf-8")
    second_html_path.write_text("<h1>Second Vacancy</h1>", encoding="utf-8")

    preprocessing_dir = tmp_path / "preprocessing"
    preprocessing_dir.mkdir()
    existing_output_path = preprocessing_dir / "a_vacancy.txt"
    existing_output_path.write_text("Already done", encoding="utf-8")

    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)
    processed_html: list[str] = []

    def fake_preprocess_job_html(raw_html: str) -> str:
        processed_html.append(raw_html)
        return raw_html.replace("<h1>", "").replace("</h1>", "").strip()

    monkeypatch.setattr(
        job_profiling_cli,
        "preprocess_job_html",
        fake_preprocess_job_html,
    )

    results = job_profiling_cli.run_job_profiling_for_input_path(
        input_path=html_dir,
        pipeline=["pre"],
        preprocessing_output_dir=preprocessing_dir,
    )

    assert [result.input_path for result in results] == [second_html_path]
    assert processed_html == ["<h1>Second Vacancy</h1>"]
    assert existing_output_path.read_text(encoding="utf-8") == "Already done"
    assert (preprocessing_dir / "b_vacancy.txt").read_text(encoding="utf-8") == (
        "Second Vacancy"
    )


def test_run_job_profiling_for_input_path_skips_existing_ext_outputs_for_pre_ext(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_dir = tmp_path / "html"
    html_dir.mkdir()
    first_html_path = html_dir / "a_vacancy.html"
    second_html_path = html_dir / "b_vacancy.html"
    first_html_path.write_text("<h1>First Vacancy</h1>", encoding="utf-8")
    second_html_path.write_text("<h1>Second Vacancy</h1>", encoding="utf-8")

    preprocessing_dir = tmp_path / "preprocessing"
    vacancy_profiles_dir = tmp_path / "vacancy_profiles"
    vacancy_profiles_dir.mkdir()
    existing_output_path = vacancy_profiles_dir / "a_vacancy.json"
    existing_output_path.write_text(
        json.dumps(_vacancy_profile_payload().model_dump(mode="json")),
        encoding="utf-8",
    )

    monkeypatch.setattr(job_profiling_cli, "log", lambda _message: None)
    processed_cleaned_texts: list[str] = []
    monkeypatch.setattr(
        job_profiling_cli,
        "preprocess_job_html",
        lambda raw_html: raw_html.replace("<h1>", "").replace("</h1>", "").strip(),
    )

    def fake_profile_vacancy_text(cleaned_text: str) -> FakeVacancyProfile:
        processed_cleaned_texts.append(cleaned_text)
        return _vacancy_profile_payload()

    monkeypatch.setattr(
        job_profiling_cli,
        "profile_vacancy_text",
        fake_profile_vacancy_text,
    )

    results = job_profiling_cli.run_job_profiling_for_input_path(
        input_path=html_dir,
        pipeline=["pre", "ext"],
        preprocessing_output_dir=preprocessing_dir,
        vacancy_profile_output_dir=vacancy_profiles_dir,
    )

    assert [result.input_path for result in results] == [second_html_path]
    assert processed_cleaned_texts == ["Second Vacancy"]
    assert existing_output_path.exists()
    assert (vacancy_profiles_dir / "b_vacancy.json").exists()
