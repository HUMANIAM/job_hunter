from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shared.llm import load_text_file, render_template

MODULE_DIR = Path(__file__).resolve().parent
JOB_PROFILE_USER_MESSAGE_PATH = MODULE_DIR / "job_profile_user_message.md"


@lru_cache(maxsize=1)
def _load_job_profile_user_message_template() -> str:
    return load_text_file(JOB_PROFILE_USER_MESSAGE_PATH)


def render_job_profile_user_message(source_text: str) -> str:
    return render_template(
        _load_job_profile_user_message_template(),
        {
            "{{SOURCE_TEXT}}": source_text.replace("```", "'''"),
        },
    )


__all__ = ["render_job_profile_user_message"]
