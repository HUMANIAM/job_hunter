from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.job_profiling import job_profiling_cli
from clients.profiling.vacancy_profile_model import VacancyProfile


def _vacancy_profile_payload() -> VacancyProfile:
    return VacancyProfile.model_validate(
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
    args = job_profiling_cli.parse_args([])

    assert args.html_path == job_profiling_cli.DEFAULT_HTML_INPUT_DIR
    assert args.pre_output_dir == job_profiling_cli.DEFAULT_PREPROCESSING_OUTPUT_DIR
    assert args.pipeline == ["pre"]


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

    def fake_profile_vacancy_text(cleaned_text: str) -> VacancyProfile:
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
        html_path=html_dir,
        pipeline=["pre"],
        preprocessing_output_dir=preprocessing_dir,
    )

    assert [result.html_path for result in results] == [first_html_path, second_html_path]
    assert (preprocessing_dir / "a_vacancy.txt").read_text(encoding="utf-8") == (
        "First Vacancy"
    )
    assert (preprocessing_dir / "b_vacancy.txt").read_text(encoding="utf-8") == (
        "Second Vacancy"
    )
