import fetch_jobs
from sources.sioux import parser as sioux_parser


def test_matched_keywords_uses_boundaries_for_short_keywords() -> None:
    # Given: a short keyword that previously matched inside a larger token
    patterns = fetch_jobs.compile_keyword_patterns(["ml"])

    # When: the helper scans unrelated text
    matched_in_asml = fetch_jobs.matched_keywords(
        "ASML careers portal", ["ml"], patterns
    )
    matched_in_ml_text = fetch_jobs.matched_keywords(
        "Experience with ML inference systems.", ["ml"], patterns
    )

    # Then: only the standalone ML mention should match
    assert matched_in_asml == []
    assert matched_in_ml_text == ["ml"]


def test_evaluate_job_skips_only_by_title() -> None:
    # Given: a software title with non-target business words in the description
    job = sioux_parser.SiouxJob(
        title="Controls Scientist",
        url="https://example.com/controls-scientist",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text=(
            "Build machine control software for lithography systems and "
            "partner with finance and supply chain stakeholders."
        ),
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: the description should not trigger a hard reject
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "title_keep_match"
    assert evaluation["title_hits"] == ["controls"]


def test_evaluate_job_rejects_skip_title_keyword() -> None:
    # Given: a title that is clearly outside the target profile
    job = sioux_parser.SiouxJob(
        title="Supply Chain Planner",
        url="https://example.com/supply-chain-planner",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text="Python dashboards and automation for operations.",
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: the skip title keyword should override keep terms
    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "skip_title_keywords"
    assert evaluation["skip_hits"] == ["supply chain", "planner"]


def test_evaluate_job_rejects_low_signal_description_only_match() -> None:
    # Given: a non-target title with only a generic description keyword
    job = sioux_parser.SiouxJob(
        title="Accounts Payable Specialist",
        url="https://example.com/accounts-payable-specialist",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text="The team is focused on control processes and approvals.",
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: a single low-signal description hit should not keep the job
    assert evaluation["decision"] == "skip"
    assert evaluation["reason"] == "insufficient_keep_signal"
    assert evaluation["description_hits"] == []


def test_evaluate_job_keeps_strong_description_only_match() -> None:
    # Given: an ambiguous title with multiple strong technical description hits
    job = sioux_parser.SiouxJob(
        title="Process Improvement Role",
        url="https://example.com/process-improvement-role",
        disciplines=[],
        location=None,
        team=None,
        work_experience=None,
        educational_background=None,
        workplace_type=None,
        fulltime_parttime=None,
        description_text=(
            "Build Python tooling for Linux-based systems and machine learning "
            "inference workflows."
        ),
    )

    # When: the job is evaluated
    evaluation = fetch_jobs.evaluate_job(job)

    # Then: multiple strong description hits should keep the job
    assert evaluation["decision"] == "keep"
    assert evaluation["reason"] == "description_keep_match"
    assert evaluation["description_hits"] == [
        "python",
        "linux",
        "machine learning",
        "inference",
    ]
