import json
from dataclasses import fields
from pathlib import Path

from sources.sioux.llm import SiouxLlmExtractionPayload
from sources.sioux.parser import SiouxJob, SiouxJobDeterministic


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


def test_jobs_sioux_schema_prompt_defs_match_runtime_models() -> None:
    schema_path = Path("sources/sioux/jobs_sioux.schema.json")

    with schema_path.open("r", encoding="utf-8") as file_handle:
        schema = json.load(file_handle)

    llm_required = schema["$defs"]["llmExtraction"]["required"]
    llm_properties = schema["$defs"]["llmExtraction"]["properties"]
    deterministic_required = schema["$defs"]["siouxJobDeterministicContext"]["required"]
    deterministic_properties = schema["$defs"]["siouxJobDeterministicContext"]["properties"]

    assert llm_required == list(SiouxLlmExtractionPayload.model_fields.keys())
    assert list(llm_properties.keys()) == list(SiouxLlmExtractionPayload.model_fields.keys())
    assert deterministic_required == [
        field.name
        for field in fields(SiouxJobDeterministic)
        if field.name != "description_text"
    ]
    assert list(deterministic_properties.keys()) == [
        field.name
        for field in fields(SiouxJobDeterministic)
        if field.name != "description_text"
    ]
