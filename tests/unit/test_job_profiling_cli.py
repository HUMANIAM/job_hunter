from __future__ import annotations

import json
from pathlib import Path

import pytest

from clients.job_profiling import job_profiling_cli
from clients.job_profiling.vacancy_profiler.vacancy_profile_model import VacancyProfile


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


def test_run_job_profiling_supports_pre_and_ext_pipeline(
    tmp_path: Path,
    monkeypatch,
) -> None:
    html_path = tmp_path / "vacancy.html"
    html_path.write_text("<h1>Mechatronics Technician</h1>", encoding="utf-8")

    preprocessing_dir = tmp_path / "preprocessing"
    vacancy_profiles_dir = tmp_path / "vacancy_profiles"
    monkeypatch.setattr(
        job_profiling_cli,
        "DEFAULT_PREPROCESSING_OUTPUT_DIR",
        preprocessing_dir,
    )
    monkeypatch.setattr(
        job_profiling_cli,
        "DEFAULT_VACANCY_PROFILE_OUTPUT_DIR",
        vacancy_profiles_dir,
    )
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

    monkeypatch.setattr(
        job_profiling_cli,
        "DEFAULT_PREPROCESSING_OUTPUT_DIR",
        tmp_path / "missing-preprocessing",
    )

    with pytest.raises(SystemExit, match="preprocessed vacancy text does not exist"):
        job_profiling_cli.run_job_profiling(
            html_path=html_path,
            pipeline=["ext"],
        )
