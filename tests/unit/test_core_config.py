from pathlib import Path

import pytest
from pydantic import ValidationError

from core import config


def test_get_settings_logs_and_raises_when_database_url_missing(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    tmp_path: Path,
) -> None:
    config.get_settings.cache_clear()
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setattr(config, "POSTGRES_ENV_FILE", tmp_path / "missing.env")
    monkeypatch.setitem(config.Settings.model_config, "env_file", tmp_path / "missing.env")

    with caplog.at_level("CRITICAL"):
        with pytest.raises(ValidationError):
            config.get_settings()

    assert "DATABASE_URL" in caplog.text
    assert "Failed to load settings" in caplog.text
    assert str(tmp_path / "missing.env") in caplog.text

    config.get_settings.cache_clear()
    monkeypatch.setitem(config.Settings.model_config, "env_file", ".env")
