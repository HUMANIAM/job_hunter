from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from eligibility import job_eligibility_view_cli


def _job_profile_payload(
    *,
    title: str = "Electro-mechanical Designer",
    url: str = "https://example.com/jobs/electro-mechanical-designer",
) -> dict[str, object]:
    return {
        "job_id": "electro_mechanical_designer__test123456",
        "title": title,
        "url": url,
        "description_text": "Electromechanical design for high-tech systems.",
    }


def test_parse_args_accepts_paths() -> None:
    args = job_eligibility_view_cli.parse_args(
        [
            "--job-profile",
            "data/job_profiles/sioux/evaluated",
            "--output-dir",
            "data/job_profiles/sioux/eligibility",
        ]
    )

    assert args.job_profile == Path("data/job_profiles/sioux/evaluated")
    assert args.output_dir == Path("data/job_profiles/sioux/eligibility")


def test_build_job_eligibility_views_writes_same_filename(tmp_path: Path) -> None:
    job_path = tmp_path / "evaluated" / "controls_engineer__abc123.json"
    job_path.parent.mkdir(parents=True)
    job_path.write_text(
        json.dumps(_job_profile_payload()),
        encoding="utf-8",
    )

    output_dir = tmp_path / "eligibility"
    fake_extractor = object()

    result = job_eligibility_view_cli.build_job_eligibility_views(
        job_profile_paths=[job_path],
        output_dir=output_dir,
        extractor=fake_extractor,
        extract_job_eligibility_view_fn=lambda payload, *, extractor: (
            SimpleNamespace(
                model_dump=lambda **_kwargs: {
                    "role_families": {"allowed": ["electromechanical design"]},
                    "locations": {"allowed": ["eindhoven"]},
                }
            )
        ),
    )

    output_path = output_dir / job_path.name
    assert result.job_profile_paths == [job_path]
    assert result.output_paths == [output_path]
    with output_path.open("r", encoding="utf-8") as file_handle:
        assert json.load(file_handle) == {
            "role_families": {"allowed": ["electromechanical design"]},
            "locations": {"allowed": ["eindhoven"]},
        }


def test_main_defaults_to_evaluated_and_eligibility_dirs(
    tmp_path: Path,
    monkeypatch,
) -> None:
    job_dir = tmp_path / "job_profiles" / "sioux" / "evaluated"
    job_dir.mkdir(parents=True)
    first_job_path = job_dir / "a_job.json"
    second_job_path = job_dir / "b_job.json"
    first_job_path.write_text(json.dumps(_job_profile_payload(title="A Job")), encoding="utf-8")
    second_job_path.write_text(json.dumps(_job_profile_payload(title="B Job")), encoding="utf-8")

    output_dir = tmp_path / "job_profiles" / "sioux" / "eligibility"
    build_calls: list[dict[str, object]] = []

    monkeypatch.setattr(job_eligibility_view_cli, "DEFAULT_JOB_PROFILE_DIR", job_dir)
    monkeypatch.setattr(job_eligibility_view_cli, "DEFAULT_OUTPUT_DIR", output_dir)
    monkeypatch.setattr(
        job_eligibility_view_cli,
        "build_job_eligibility_views",
        lambda **kwargs: (
            build_calls.append(kwargs)
            or job_eligibility_view_cli.BuildJobEligibilityViewsResult(
                job_profile_paths=list(kwargs["job_profile_paths"]),
                output_paths=[output_dir / path.name for path in kwargs["job_profile_paths"]],
            )
        ),
    )
    monkeypatch.setattr(job_eligibility_view_cli, "log", lambda _message: None)

    job_eligibility_view_cli.main([])

    assert build_calls == [
        {
            "job_profile_paths": [first_job_path, second_job_path],
            "output_dir": output_dir,
            "log_message": job_eligibility_view_cli.log,
        }
    ]
