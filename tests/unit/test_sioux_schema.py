import json
from dataclasses import fields
from pathlib import Path

from sources.sioux.parser_back import SiouxJob


def test_jobs_sioux_schema_matches_kept_payload_shape() -> None:
    schema_path = Path("sources/sioux/jobs_sioux.schema.json")

    with schema_path.open("r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)

    assert schema["required"] == [
        "fetched_at_unix",
        "source",
        "configured_countries",
        "configured_languages",
        "total_jobs",
        "relevant_jobs",
        "jobs",
    ]

    job_required = schema["$defs"]["siouxJob"]["required"]
    job_properties = schema["$defs"]["siouxJob"]["properties"]
    expected_job_fields = [field.name for field in fields(SiouxJob)]

    assert job_required == expected_job_fields
    assert list(job_properties.keys()) == expected_job_fields
