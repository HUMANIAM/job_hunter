from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from clients.candidate_profiling.candidate_profile_schema import CandidateProfile
from clients.profiling import extract_profile
from shared.llm import load_text_file, render_template

MODULE_DIR = Path(__file__).resolve().parent
CANDIDATE_PROFILE_USER_MESSAGE_PATH = MODULE_DIR / "candidate_profile_user_message.md"


@lru_cache(maxsize=1)
def _load_candidate_profile_user_message_template() -> str:
    return load_text_file(CANDIDATE_PROFILE_USER_MESSAGE_PATH)


def render_candidate_profile_user_message(candidate_text: str) -> str:
    return render_template(
        _load_candidate_profile_user_message_template(),
        {
            "{{SOURCE_TEXT}}": candidate_text.replace("```", "'''"),
        },
    )


def profile_candidate_text(candidate_text: str) -> CandidateProfile:
    return extract_profile(
        candidate_text,
        profile_model=CandidateProfile,
        profile_llm_user_message=render_candidate_profile_user_message(
            candidate_text
        ),
    )


__all__ = [
    "profile_candidate_text",
    "render_candidate_profile_user_message",
]
