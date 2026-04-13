from __future__ import annotations

from clients.job_profiling.profiling.job_profile_user_message import (
    render_job_profile_user_message,
)
from clients.job_profiling.profiling.job_profile_model import VacancyProfile
from clients.profiling import extract_profile


def profile_vacancy_text(cleaned_vacancy_text: str) -> VacancyProfile:
    return extract_profile(
        cleaned_vacancy_text,
        profile_model=VacancyProfile,
        profile_llm_user_message=render_job_profile_user_message(
            cleaned_vacancy_text
        ),
    )


__all__ = ["profile_vacancy_text"]
