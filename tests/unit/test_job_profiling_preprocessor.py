from __future__ import annotations

from types import SimpleNamespace

from clients.job_profiling.preprocessing import job_profiling_preporcessor as preprocessor_module
from clients.job_profiling.preprocessing.cleaned_job_html import CleanedJobHtml
from clients.job_profiling.preprocessing.job_profiling_preporcessor import (
    DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS,
    JobProfilingPreprocessor,
    _JOB_HTML_SIGNAL_CLEANER_LLM_MODEL,
    _load_system_message,
    _render_user_message,
)


def test_job_html_signal_cleaner_system_message_requires_structured_json() -> None:
    system_message = _load_system_message()

    assert "configured response schema" in system_message
    assert "do not output JSON" not in system_message
    assert "- `html_tag`: the original HTML tag name from the visible source" in system_message
    assert "Do not copy JSON-LD, meta tags, title tags, or other document metadata" in system_message
    assert "source_kind" not in system_message


def test_job_html_signal_cleaner_user_message_includes_raw_html() -> None:
    rendered = _render_user_message("<h1>Mechatronics Technician</h1>")

    assert "{{RAW_JOB_HTML}}" not in rendered
    assert "<h1>Mechatronics Technician</h1>" in rendered
    assert "Return exactly one JSON object." in rendered
    assert "Each line item must include `html_tag` and `text`." in rendered
    assert "source_kind" not in rendered


def test_job_profiling_preprocessor_renders_structured_llm_output_as_text() -> None:
    calls: list[dict[str, object]] = []

    class FakeCompletions:
        def parse(self, **kwargs: object) -> object:
            calls.append(kwargs)
            return SimpleNamespace(
                choices=[
                    SimpleNamespace(
                        message=SimpleNamespace(
                            parsed=CleanedJobHtml.model_validate(
                                {
                                    "lines": [
                                        {
                                            "html_tag": " H1 ",
                                            "text": " Mechatronics Technician ",
                                        },
                                        {
                                            "html_tag": "p",
                                            "text": "Build high-tech modules.",
                                        },
                                    ]
                                }
                            ),
                            refusal=None,
                        )
                    )
                ]
            )

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    preprocessor = JobProfilingPreprocessor(
        client=fake_client,
        model="gpt-test",
        timeout_seconds=9.0,
        max_completion_tokens=123,
    )

    cleaned_text = preprocessor.preprocess("<h1>Mechatronics Technician</h1>")

    assert (
        cleaned_text
        == "h1: Mechatronics Technician\n"
        "p: Build high-tech modules."
    )
    assert calls == [
        {
            "model": "gpt-test",
            "n": 1,
            "temperature": 0.0,
            "presence_penalty": 0,
            "frequency_penalty": 0,
            "max_completion_tokens": 123,
            "store": False,
            "response_format": CleanedJobHtml,
            "messages": [
                {
                    "role": "system",
                    "content": _load_system_message(),
                },
                {
                    "role": "user",
                    "content": _render_user_message(
                        "<h1>Mechatronics Technician</h1>"
                    ),
                },
            ],
            "timeout": 9.0,
        }
    ]


def test_job_profiling_preprocessor_defaults_target_mini_model() -> None:
    assert _JOB_HTML_SIGNAL_CLEANER_LLM_MODEL == "gpt-5.4-mini"
    assert DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS == 4000


def test_job_profiling_preprocessor_exports_current_factory_name() -> None:
    assert "get_job_profiling_preprocessor" in preprocessor_module.__all__
    assert "get_default_job_profiling_preprocessor" not in preprocessor_module.__all__
