from __future__ import annotations

import json
from pathlib import Path

from app import rerank_jobs


def _candidate_profile_payload(candidate_id: str = "Ibrahim_Saad_CV") -> dict[str, object]:
    return {
        "candidate_id": candidate_id,
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


def _job_profile_payload(
    *,
    job_id: str = "controls_engineer__test123456",
    title: str = "Controls Engineer",
    url: str = "https://example.com/jobs/controls",
) -> dict[str, object]:
    return {
        "job_id": job_id,
        "title": title,
        "url": url,
    }


def _ranking_result(
    *,
    job_id: str = "controls_engineer__test123456",
    candidate_id: str = "Ibrahim_Saad_CV",
    status: str = "match",
    decision_stage: str = "ranking",
) -> dict[str, object]:
    return {
        "job_id": job_id,
        "candidate_id": candidate_id,
        "score": 0.91 if status == "match" else 0.0,
        "status": status,
        "decision_stage": decision_stage,
        "bucket_scores": {
            "skills": 0.9,
            "languages": 0.8,
            "protocols": 0.7,
            "standards": 0.0,
            "domains": 0.6,
            "seniority": 0.9,
            "years_experience": 0.8,
        },
        "matched_features": [],
        "missing_features": [],
        "rejection_reasons": [] if status == "match" else [
            {
                "stage": decision_stage,
                "bucket": "skills",
                "reason": "required_feature_missing",
                "expected": "python",
                "actual": None,
            }
        ],
    }


def test_parse_args_accepts_specific_paths() -> None:
    args = rerank_jobs.parse_args(
        [
            "--job-profile",
            "data/job_profiles/sioux/evaluated/job.json",
            "--candidate-profile",
            "data/candidate_profiles/Ibrahim_Saad_CV.json",
        ]
    )

    assert args.job_profile == Path("data/job_profiles/sioux/evaluated/job.json")
    assert args.candidate_profile == Path("data/candidate_profiles/Ibrahim_Saad_CV.json")


def test_main_defaults_to_job_and_candidate_json_dirs(tmp_path: Path, monkeypatch) -> None:
    candidate_dir = tmp_path / "candidate_profiles"
    candidate_dir.mkdir()
    candidate_path = candidate_dir / "Ibrahim_Saad_CV.json"
    candidate_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )

    job_dir = tmp_path / "job_profiles" / "sioux" / "evaluated"
    job_dir.mkdir(parents=True)
    job_path = job_dir / "controls_engineer__test123456.json"
    job_path.write_text(
        json.dumps(_job_profile_payload()),
        encoding="utf-8",
    )

    ranking_writes: list[tuple[dict[str, object], str]] = []
    monkeypatch.setattr(rerank_jobs, "DEFAULT_CANDIDATE_PROFILE_DIR", candidate_dir)
    monkeypatch.setattr(rerank_jobs, "DEFAULT_JOB_PROFILE_DIR", job_dir)
    monkeypatch.setattr(
        rerank_jobs,
        "rank_job",
        lambda *_args, **_kwargs: _ranking_result(),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_ranking_result",
        lambda payload, *, company_slug, **_: ranking_writes.append((payload, company_slug)),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_match_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy match job artifacts should not be written")
        ),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_mismatch_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy mismatch job artifacts should not be written")
        ),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "match_job_output_path_for",
        lambda *_args, **_kwargs: tmp_path / "unused-match.json",
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "mismatch_job_output_path_for",
        lambda *_args, **_kwargs: tmp_path / "unused-mismatch.json",
    )
    monkeypatch.setattr(rerank_jobs, "log", lambda _message: None)

    rerank_jobs.main([])

    assert len(ranking_writes) == 1
    assert ranking_writes[0][0]["job_id"] == "controls_engineer__test123456"
    assert ranking_writes[0][1] == "sioux"


def test_rerank_job_profiles_removes_stale_opposite_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    candidate_path = tmp_path / "Ibrahim_Saad_CV.json"
    candidate_path.write_text(
        json.dumps(_candidate_profile_payload()),
        encoding="utf-8",
    )
    job_path = tmp_path / "job_profiles" / "sioux" / "evaluated" / "controls.json"
    job_path.parent.mkdir(parents=True)
    job_path.write_text(
        json.dumps(_job_profile_payload()),
        encoding="utf-8",
    )

    stale_match_path = tmp_path / "stale-match.json"
    stale_match_path.write_text("stale", encoding="utf-8")
    monkeypatch.setattr(
        rerank_jobs,
        "rank_job",
        lambda *_args, **_kwargs: _ranking_result(
            status="mismatch",
            decision_stage="job_must_have",
        ),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_ranking_result",
        lambda *_args, **_kwargs: None,
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_match_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy match job artifacts should not be written")
        ),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "write_mismatch_job",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy mismatch job artifacts should not be written")
        ),
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "match_job_output_path_for",
        lambda *_args, **_kwargs: stale_match_path,
    )
    monkeypatch.setattr(
        rerank_jobs.report_writer,
        "mismatch_job_output_path_for",
        lambda *_args, **_kwargs: tmp_path / "new-mismatch.json",
    )

    rerank_jobs.rerank_job_profiles(
        candidate_profile_paths=[candidate_path],
        job_profile_paths=[job_path],
    )

    assert stale_match_path.exists() is False
