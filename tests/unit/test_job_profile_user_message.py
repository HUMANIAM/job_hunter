from __future__ import annotations

from clients.job_profiling.profiling.job_profile_user_message import (
    render_job_profile_user_message,
)


def test_render_job_profile_user_message_includes_cleaned_text() -> None:
    rendered = render_job_profile_user_message("h1: Mechatronics Technician")

    assert "{{SOURCE_TEXT}}" not in rendered
    assert "h1: Mechatronics Technician" in rendered
    assert "primary should be the single best professional role" in rendered


def test_render_job_profile_user_message_replaces_triple_backticks() -> None:
    rendered = render_job_profile_user_message("```danger```")

    assert "```" not in rendered
    assert "'''danger'''" in rendered
