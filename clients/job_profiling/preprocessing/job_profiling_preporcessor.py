from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from openai import OpenAI

from shared.env import require_env_value
from shared.llm import load_text_file, render_template

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


class JobProfilingPreprocessor:
    def __init__(
        self,
        *,
        client: OpenAI,
    ) -> None:
        self._client = client
        self._system_message = _load_system_message()

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
        user_message = _render_user_message(raw_job_html)
        completion = self._client.chat.completions.create(
            model=_JOB_HTML_SIGNAL_CLEANER_LLM_MODEL,
            n=1,
            temperature=0.0,
            presence_penalty=0,
            frequency_penalty=0,
            max_completion_tokens=DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS,
            store=False,
            messages=[
                {"role": "system", "content": self._system_message},
                {"role": "user", "content": user_message},
            ],
            timeout=_JOB_HTML_SIGNAL_CLEANER_TIMEOUT_SECONDS,
        )
        message = completion.choices[0].message
        refusal = getattr(message, "refusal", None)
        if refusal:
            raise RuntimeError(f"Job HTML signal cleaning refused the request: {refusal}")

        if not message.content:
            raise RuntimeError("Job HTML signal cleaning returned empty content")

        return message.content


@lru_cache(maxsize=1)
def get_default_job_profiling_preprocessor() -> JobProfilingPreprocessor:
    return JobProfilingPreprocessor.create()


def preprocess_job_html(
    raw_job_html: str,
    *,
    preprocessor: JobProfilingPreprocessor | None = None,
) -> str:
    active_preprocessor = preprocessor or get_default_job_profiling_preprocessor()
    return active_preprocessor.preprocess(raw_job_html)


__all__ = [
    "DEFAULT_JOB_HTML_SIGNAL_CLEANER_MAX_COMPLETION_TOKENS",
    "JobProfilingPreprocessor",
    "get_default_job_profiling_preprocessor",
    "preprocess_job_html",
]
