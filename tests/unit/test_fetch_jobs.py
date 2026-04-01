from __future__ import annotations

from dataclasses import dataclass

from ranking import evaluator as ranking_evaluator


@dataclass
class FakeJob:
    title: str | None
    description_text: str | None
    required_languages: list[str] | None = None
    restrictions: list[str] | None = None
    min_years_experience: int | None = None


def test_matched_keywords_uses_boundaries_for_short_keywords() -> None:
    # Given: a short keyword that previously matched inside a larger token
    patterns = ranking_evaluator.compile_keyword_patterns(["ml"])

    # When: the helper scans unrelated text
    matched_in_asml = ranking_evaluator.matched_keywords(
        "ASML careers portal", ["ml"], patterns
    )
    matched_in_ml_text = ranking_evaluator.matched_keywords(
        "Experience with ML inference systems.", ["ml"], patterns
    )

    # Then: only the standalone ML mention should match
    assert matched_in_asml == []
    assert matched_in_ml_text == ["ml"]


def test_evaluate_job_skips_only_by_title() -> None:
    # Given: a software title with non-target business words in the description
    job = FakeJob(
        title="Controls Scientist",
        description_text=(
            "Build machine control software for lithography systems and "
            "partner with finance and supply chain stakeholders."
        ),
    )

    # When: the job is evaluated
    evaluation = ranking_evaluator.evaluate_job(job)

    # Then: the description should not trigger a hard reject
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "title_keep_match"
    assert evaluation["title_hits"] == ["controls"]


def test_evaluate_job_can_keep_non_target_title_from_description_signal() -> None:
    # Given: a non-target title with strong technical description keywords
    job = FakeJob(
        title="Supply Chain Planner",
        description_text="Python dashboards and automation for operations.",
    )

    # When: the job is evaluated
    evaluation = ranking_evaluator.evaluate_job(job)

    # Then: the title alone should not force a reject anymore
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "description_keep_match"
    assert evaluation["skip_hits"] == []
    assert evaluation["description_hits"] == ["python", "automation"]


def test_evaluate_job_skips_excluded_job_type_before_keyword_matching() -> None:
    job = FakeJob(
        title="Embedded Software Internship",
        description_text="Python and Linux work on machine learning systems.",
    )

    evaluation = ranking_evaluator.evaluate_job(job)

    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "hard_filter_exclude_job_type"
    assert evaluation["skip_hits"] == ["job_type:internship"]
    assert evaluation["title_hits"] == []
    assert evaluation["description_hits"] == []


def test_evaluate_job_skips_excluded_required_language_before_keyword_matching() -> None:
    job = FakeJob(
        title="Embedded Software Engineer",
        description_text="Python and Linux work on machine learning systems.",
        required_languages=["english", "dutch"],
    )

    evaluation = ranking_evaluator.evaluate_job(job)

    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "hard_filter_required_language"
    assert evaluation["skip_hits"] == ["required_language:dutch"]
    assert evaluation["title_hits"] == []
    assert evaluation["description_hits"] == []


def test_evaluate_job_skips_when_min_years_experience_exceeds_limit() -> None:
    job = FakeJob(
        title="Embedded Software Engineer",
        description_text="Python and Linux work on machine learning systems.",
        min_years_experience=8,
    )

    evaluation = ranking_evaluator.evaluate_job(job)

    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "hard_filter_min_years_experience"
    assert evaluation["skip_hits"] == ["min_years_experience:8"]
    assert evaluation["title_hits"] == []
    assert evaluation["description_hits"] == []


def test_evaluate_job_skips_export_control_clearance_restriction() -> None:
    job = FakeJob(
        title="Embedded Software Engineer",
        description_text="Python and Linux work on machine learning systems.",
        restrictions=["eligible for Dutch security clearance"],
    )

    evaluation = ranking_evaluator.evaluate_job(job)

    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "hard_filter_export_control_clearance"
    assert evaluation["skip_hits"] == [
        "restriction:export_control_or_security_clearance"
    ]
    assert evaluation["title_hits"] == []
    assert evaluation["description_hits"] == []


def test_evaluate_job_rejects_low_signal_description_only_match() -> None:
    # Given: a non-target title with only a generic description keyword
    job = FakeJob(
        title="Accounts Payable Specialist",
        description_text="The team is focused on control processes and approvals.",
    )

    # When: the job is evaluated
    evaluation = ranking_evaluator.evaluate_job(job)

    # Then: a single low-signal description hit should not keep the job
    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "insufficient_keep_signal"
    assert evaluation["description_hits"] == []


def test_evaluate_job_keeps_strong_description_only_match() -> None:
    # Given: an ambiguous title with multiple strong technical description hits
    job = FakeJob(
        title="Process Improvement Role",
        description_text=(
            "Build Python tooling for Linux-based systems and machine learning "
            "inference workflows."
        ),
    )

    # When: the job is evaluated
    evaluation = ranking_evaluator.evaluate_job(job)

    # Then: multiple strong description hits should keep the job
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "description_keep_match"
    assert evaluation["description_hits"] == [
        "python",
        "linux",
        "machine learning",
        "inference",
    ]
