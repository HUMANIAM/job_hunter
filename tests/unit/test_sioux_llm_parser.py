from __future__ import annotations

from sources.sioux import parser as sioux_parser
from sources.sioux.llm import SiouxLlmExtractionPayload, render_llm_user_message


def test_render_llm_user_message_serializes_nullable_context() -> None:
    job = sioux_parser.SiouxJobDeterministic(
        title="Systems Engineer",
        url="https://vacancy.sioux.eu/vacancies/systems-engineer.html",
        disciplines=["Controls"],
        location=None,
        team=None,
        work_experience=None,
        min_years_experience=None,
        max_years_experience=None,
        experience_text=None,
        educational_background=None,
        required_degrees=[],
        industry_domains=[],
        workplace_type=None,
        fulltime_parttime=None,
        min_hours_per_week=None,
        max_hours_per_week=None,
        remote_policy=None,
        work_locations_text=None,
        client_site_required=None,
        travel_region=None,
        recruiter_name=None,
        recruiter_role=None,
        recruiter_email=None,
        recruiter_phone=None,
        description_text="Generic systems role without explicit technical details.",
    )

    rendered = render_llm_user_message(job)

    assert "{{llm_output_schema_json}}" not in rendered
    assert "{{deterministic_fields_json}}" not in rendered
    assert '"location": null' in rendered
    assert '"client_site_required": null' in rendered
    assert '"disciplines": [' in rendered
    assert '"Controls"' in rendered
    assert (
        '"seniority_hint": "junior | medior | senior | lead | principal | staff | null"'
        in rendered
    )
    assert "Generic systems role without explicit technical details." in rendered


def test_fetch_job_combines_deterministic_and_llm_fields() -> None:
    deterministic_job = sioux_parser.SiouxJobDeterministic(
        title="Embedded Software Engineer",
        url="https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        disciplines=["Embedded", "Software"],
        location="Eindhoven",
        team="Embedded Systems",
        work_experience="Senior",
        min_years_experience=5,
        max_years_experience=None,
        experience_text="At least 5 years of experience in embedded software.",
        educational_background="Bachelor",
        required_degrees=["Bachelor"],
        industry_domains=["Semiconductor", "Medical"],
        workplace_type="Hybrid",
        fulltime_parttime="Full time",
        min_hours_per_week=32,
        max_hours_per_week=40,
        remote_policy="Hybrid",
        work_locations_text="From our office in Eindhoven and on-site at clients",
        client_site_required=True,
        travel_region="Brainport region",
        recruiter_name="Jettine van Dongen",
        recruiter_role="Talent acquisition",
        recruiter_email="jobs@sioux.eu",
        recruiter_phone="+31 (0)40 - 2677100",
        description_text="Senior embedded role for semiconductor systems.",
    )

    class FakeExtractor:
        def extract(
            self,
            job: sioux_parser.SiouxJobDeterministic,
        ) -> SiouxLlmExtractionPayload:
            assert job == deterministic_job
            return SiouxLlmExtractionPayload.model_validate(
                {
                    "required_skills": ["c++", "embedded linux"],
                    "preferred_skills": ["qt"],
                    "required_languages": ["english"],
                    "preferred_languages": ["dutch"],
                    "required_protocols": ["can"],
                    "preferred_protocols": ["ethercat"],
                    "required_standards": ["iec 61508"],
                    "preferred_standards": ["misra"],
                    "required_domains": ["semiconductor"],
                    "preferred_domains": ["medical devices"],
                    "seniority_hint": "senior",
                    "restrictions": ["eu work authorization"],
                    "evidence": {
                        "required_skills": ["experience with C++ and Embedded Linux"],
                        "preferred_skills": ["Qt is a plus"],
                        "required_languages": ["fluent in English"],
                        "preferred_languages": ["Dutch is a plus"],
                        "required_protocols": ["knowledge of CAN"],
                        "preferred_protocols": ["EtherCAT is a plus"],
                        "required_standards": ["IEC 61508"],
                        "preferred_standards": ["MISRA is a plus"],
                        "required_domains": ["semiconductor systems"],
                        "preferred_domains": ["medical devices is a plus"],
                        "seniority_hint": ["Senior embedded software engineer"],
                        "restrictions": ["must already have EU work authorization"],
                    },
                }
            )

    messages: list[str] = []

    original_fetch = sioux_parser.fetch_job_deterministic
    sioux_parser.fetch_job_deterministic = lambda *_args, **_kwargs: deterministic_job
    try:
        job = sioux_parser.fetch_job(
            object(),
            deterministic_job.url,
            disciplines=deterministic_job.disciplines,
            log_message=messages.append,
            llm_extractor=FakeExtractor(),
        )
    finally:
        sioux_parser.fetch_job_deterministic = original_fetch

    assert job == sioux_parser.SiouxJob(
        title="Embedded Software Engineer",
        url="https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        disciplines=["Embedded", "Software"],
        location="Eindhoven",
        team="Embedded Systems",
        work_experience="Senior",
        min_years_experience=5,
        max_years_experience=None,
        experience_text="At least 5 years of experience in embedded software.",
        educational_background="Bachelor",
        required_degrees=["Bachelor"],
        required_languages=["english"],
        preferred_languages=["dutch"],
        required_protocols=["can"],
        preferred_protocols=["ethercat"],
        required_standards=["iec 61508"],
        preferred_standards=["misra"],
        industry_domains=["Semiconductor", "Medical"],
        required_domains=["semiconductor"],
        preferred_domains=["medical devices"],
        workplace_type="Hybrid",
        fulltime_parttime="Full time",
        min_hours_per_week=32,
        max_hours_per_week=40,
        remote_policy="Hybrid",
        work_locations_text="From our office in Eindhoven and on-site at clients",
        client_site_required=True,
        travel_region="Brainport region",
        recruiter_name="Jettine van Dongen",
        recruiter_role="Talent acquisition",
        recruiter_email="jobs@sioux.eu",
        recruiter_phone="+31 (0)40 - 2677100",
        required_skills=["c++", "embedded linux"],
        preferred_skills=["qt"],
        seniority_hint="senior",
        restrictions=["eu work authorization"],
        evidence=sioux_parser.SiouxJobLlmEvidence(
            required_skills=["experience with C++ and Embedded Linux"],
            preferred_skills=["Qt is a plus"],
            required_languages=["fluent in English"],
            preferred_languages=["Dutch is a plus"],
            required_protocols=["knowledge of CAN"],
            preferred_protocols=["EtherCAT is a plus"],
            required_standards=["IEC 61508"],
            preferred_standards=["MISRA is a plus"],
            required_domains=["semiconductor systems"],
            preferred_domains=["medical devices is a plus"],
            seniority_hint=["Senior embedded software engineer"],
            restrictions=["must already have EU work authorization"],
        ),
        description_text="Senior embedded role for semiconductor systems.",
    )
    assert "required_protocols=['can']" in messages[-1]
    assert "seniority_hint='senior'" in messages[-1]
