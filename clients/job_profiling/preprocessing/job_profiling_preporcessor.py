from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Dict

from openai import OpenAI

from clients.job_profiling.preprocessing.cleaned_job_html import CleanedJobHtml
from shared.env import require_env_value
from shared.llm import OpenAIStructuredExtractor, load_text_file, render_template

_JOB_HTML_SIGNAL_CLEANER_LLM_MODEL = "gpt-5.4-mini"
DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS = 4000
_JOB_HTML_SIGNAL_CLEANER_TIMEOUT_SECONDS = 60.0

MODULE_DIR = Path(__file__).resolve().parent

SYSTEM_MESSAGE_PATH = MODULE_DIR / "system_message.md"
USER_MESSAGE_PATH = MODULE_DIR / "user_message.md"


@lru_cache(maxsize=1)
def _load_system_message() -> str:
    return load_text_file(SYSTEM_MESSAGE_PATH)


@lru_cache(maxsize=1)
def _load_user_message_template() -> str:
    return load_text_file(USER_MESSAGE_PATH)


def _render_user_message(raw_job_html: str) -> str:
    template = _load_user_message_template()
    return render_template(
        template,
        {
            "{{RAW_JOB_HTML}}": raw_job_html,
        },
    )


def _build_extraction_payload(raw_job_html: str) -> Dict[str, str]:
    return {
        "raw_job_html": raw_job_html,
    }


def _render_extractor_user_message(payload: Dict[str, str]) -> str:
    return _render_user_message(payload["raw_job_html"])


def _render_cleaned_job_html(cleaned_job_html: CleanedJobHtml) -> str:
    return "\n".join(
        f"{line.source_kind}|{line.html_tag}: {line.text}"
        for line in cleaned_job_html.lines
    )


class JobProfilingPreprocessor:
    def __init__(
        self,
        *,
        client: OpenAI,
        model: str = _JOB_HTML_SIGNAL_CLEANER_LLM_MODEL,
        max_completion_tokens: int = DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS,
        timeout_seconds: float = _JOB_HTML_SIGNAL_CLEANER_TIMEOUT_SECONDS,
    ) -> None:
        self._extractor = OpenAIStructuredExtractor(
            client=client,
            model=model,
            response_format=CleanedJobHtml,
            system_message=_load_system_message(),
            render_user_message=_render_extractor_user_message,
            operation_name="Job HTML signal cleaning",
            timeout_seconds=timeout_seconds,
            max_completion_tokens=max_completion_tokens,
        )

    @classmethod
    def create(cls) -> JobProfilingPreprocessor:
        api_key = require_env_value(
            "OPENAI_API_KEY",
            error_context="Job HTML signal cleaning",
        )
        return cls(
            client=OpenAI(api_key=api_key),
        )

    def preprocess(self, raw_job_html: str) -> str:
        cleaned_job_html = self._extractor.extract(
            _build_extraction_payload(raw_job_html)
        )
        return _render_cleaned_job_html(cleaned_job_html)


@lru_cache(maxsize=1)
def get_job_profiling_preprocessor() -> JobProfilingPreprocessor:
    return JobProfilingPreprocessor.create()


def preprocess_job_html(raw_job_html: str) -> str:
    preprocessor = get_job_profiling_preprocessor()
    return preprocessor.preprocess(raw_job_html)


__all__ = [
    "DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS",
    "JobProfilingPreprocessor",
    "get_job_profiling_preprocessor",
    "preprocess_job_html",
]
