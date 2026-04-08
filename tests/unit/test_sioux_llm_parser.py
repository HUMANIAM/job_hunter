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
    assert '"requirement_level": "required | preferred"' in rendered
    assert '"seniority": {' in rendered
    assert (
        '"value": "junior | medior | senior | lead | principal | staff | null"'
        in rendered
    )
    assert "Generic systems role without explicit technical details." in rendered


def test_sioux_llm_payload_normalizes_fields() -> None:
    payload = SiouxLlmExtractionPayload.model_validate(
        {
            "skills": [
                {
                    "name": "  C++  ",
                    "requirement_level": " Required ",
                    "confidence": " 0.96 ",
                    "evidence": [" Experience with C++ "],
                }
            ],
            "languages": [
                {
                    "name": " English ",
                    "requirement_level": " preferred ",
                    "confidence": 0.74,
                    "evidence": ["Fluent in English"],
                }
            ],
            "protocols": [],
            "standards": [],
            "domains": [],
            "seniority": {
                "value": " Senior ",
                "confidence": 0.91,
                "evidence": ["Senior embedded role"],
            },
            "restrictions": [
                {
                    "value": " EU Work Authorization ",
                    "confidence": 0.82,
                    "evidence": ["Must already have EU work authorization"],
                }
            ],
        }
    )

    assert payload.skills[0].name == "c++"
    assert payload.skills[0].requirement_level == "required"
    assert payload.skills[0].confidence == 0.96
    assert payload.skills[0].evidence == ["Experience with C++"]
    assert payload.languages[0].name == "english"
    assert payload.languages[0].requirement_level == "preferred"
    assert payload.seniority.value == "senior"
    assert payload.restrictions[0].value == "eu work authorization"


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
                    "skills": [
                        {
                            "name": "c++",
                            "requirement_level": "required",
                            "confidence": 0.96,
                            "evidence": ["experience with C++ and Embedded Linux"],
                        },
                        {
                            "name": "embedded linux",
                            "requirement_level": "required",
                            "confidence": 0.95,
                            "evidence": ["experience with C++ and Embedded Linux"],
                        },
                        {
                            "name": "qt",
                            "requirement_level": "preferred",
                            "confidence": 0.82,
                            "evidence": ["Qt is a plus"],
                        },
                    ],
                    "languages": [
                        {
                            "name": "english",
                            "requirement_level": "required",
                            "confidence": 0.94,
                            "evidence": ["fluent in English"],
                        },
                        {
                            "name": "dutch",
                            "requirement_level": "preferred",
                            "confidence": 0.74,
                            "evidence": ["Dutch is a plus"],
                        },
                    ],
                    "protocols": [
                        {
                            "name": "can",
                            "requirement_level": "required",
                            "confidence": 0.91,
                            "evidence": ["knowledge of CAN"],
                        },
                        {
                            "name": "ethercat",
                            "requirement_level": "preferred",
                            "confidence": 0.76,
                            "evidence": ["EtherCAT is a plus"],
                        },
                    ],
                    "standards": [
                        {
                            "name": "iec 61508",
                            "requirement_level": "required",
                            "confidence": 0.9,
                            "evidence": ["IEC 61508"],
                        },
                        {
                            "name": "misra",
                            "requirement_level": "preferred",
                            "confidence": 0.8,
                            "evidence": ["MISRA is a plus"],
                        },
                    ],
                    "domains": [
                        {
                            "name": "semiconductor",
                            "requirement_level": "required",
                            "confidence": 0.88,
                            "evidence": ["semiconductor systems"],
                        },
                        {
                            "name": "medical devices",
                            "requirement_level": "preferred",
                            "confidence": 0.77,
                            "evidence": ["medical devices is a plus"],
                        },
                    ],
                    "seniority": {
                        "value": "senior",
                        "confidence": 0.93,
                        "evidence": ["Senior embedded software engineer"],
                    },
                    "restrictions": [
                        {
                            "value": "eu work authorization",
                            "confidence": 0.95,
                            "evidence": ["must already have EU work authorization"],
                        }
                    ],
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
        job_id=sioux_parser.compute_job_id(
            "Embedded Software Engineer",
            "https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        ),
        title="Embedded Software Engineer",
        url="https://vacancy.sioux.eu/vacancies/embedded-software-engineer.html",
        disciplines=["Embedded", "Software"],
        location="Eindhoven",
        team="Embedded Systems",
        work_experience="Senior",
        years_experience_requirement=sioux_parser.SiouxJobYearsExperienceRequirement(
            min_years=5,
            max_years=None,
            requirement_level="required",
            confidence=0.9,
            evidence=["At least 5 years of experience in embedded software."],
            source_kind="regex_text",
        ),
        educational_background="Bachelor",
        required_degrees=["Bachelor"],
        skills=[
            sioux_parser.SiouxJobFeature(
                name="c++",
                requirement_level="required",
                confidence=0.96,
                evidence=["experience with C++ and Embedded Linux"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="embedded linux",
                requirement_level="required",
                confidence=0.95,
                evidence=["experience with C++ and Embedded Linux"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="qt",
                requirement_level="preferred",
                confidence=0.82,
                evidence=["Qt is a plus"],
                source_kind="llm",
            ),
        ],
        languages=[
            sioux_parser.SiouxJobFeature(
                name="english",
                requirement_level="required",
                confidence=0.94,
                evidence=["fluent in English"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="dutch",
                requirement_level="preferred",
                confidence=0.74,
                evidence=["Dutch is a plus"],
                source_kind="llm",
            ),
        ],
        protocols=[
            sioux_parser.SiouxJobFeature(
                name="can",
                requirement_level="required",
                confidence=0.91,
                evidence=["knowledge of CAN"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="ethercat",
                requirement_level="preferred",
                confidence=0.76,
                evidence=["EtherCAT is a plus"],
                source_kind="llm",
            ),
        ],
        standards=[
            sioux_parser.SiouxJobFeature(
                name="iec 61508",
                requirement_level="required",
                confidence=0.9,
                evidence=["IEC 61508"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="misra",
                requirement_level="preferred",
                confidence=0.8,
                evidence=["MISRA is a plus"],
                source_kind="llm",
            ),
        ],
        industry_domains=["Semiconductor", "Medical"],
        domains=[
            sioux_parser.SiouxJobFeature(
                name="semiconductor",
                requirement_level="required",
                confidence=0.88,
                evidence=["semiconductor systems"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobFeature(
                name="medical devices",
                requirement_level="preferred",
                confidence=0.77,
                evidence=["medical devices is a plus"],
                source_kind="llm",
            ),
        ],
        job_constraints=[
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="skills",
                value="c++",
                min_years=None,
                confidence=0.96,
                evidence=["experience with C++ and Embedded Linux"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="skills",
                value="embedded linux",
                min_years=None,
                confidence=0.95,
                evidence=["experience with C++ and Embedded Linux"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="languages",
                value="english",
                min_years=None,
                confidence=0.94,
                evidence=["fluent in English"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="protocols",
                value="can",
                min_years=None,
                confidence=0.91,
                evidence=["knowledge of CAN"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="standards",
                value="iec 61508",
                min_years=None,
                confidence=0.9,
                evidence=["IEC 61508"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="feature",
                bucket="domains",
                value="semiconductor",
                min_years=None,
                confidence=0.88,
                evidence=["semiconductor systems"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="seniority",
                bucket="seniority",
                value="senior",
                min_years=None,
                confidence=0.93,
                evidence=["Senior embedded software engineer"],
                source_kind="llm",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="years_experience",
                bucket="years_experience",
                value=None,
                min_years=5,
                confidence=0.9,
                evidence=["At least 5 years of experience in embedded software."],
                source_kind="regex_text",
            ),
            sioux_parser.SiouxJobConstraint(
                kind="restriction",
                bucket="restrictions",
                value="work_authorization",
                min_years=None,
                confidence=0.95,
                evidence=["must already have EU work authorization"],
                source_kind="llm",
            ),
        ],
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
        seniority=sioux_parser.SiouxJobSeniority(
            value="senior",
            confidence=0.93,
            evidence=["Senior embedded software engineer"],
            source_kind="llm",
        ),
        restrictions=[
            sioux_parser.SiouxJobRestriction(
                value="eu work authorization",
                confidence=0.95,
                evidence=["must already have EU work authorization"],
                source_kind="llm",
            )
        ],
        description_text="Senior embedded role for semiconductor systems.",
    )
    assert "languages=2" in messages[-1]
    assert "seniority='senior'" in messages[-1]
