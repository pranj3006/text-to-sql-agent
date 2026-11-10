import pytest

from text_to_sql_agent.app.core.config import Settings


def test_settings_load_database_url_without_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = "postgresql+asyncpg://user:password@localhost/example"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == database_url
    assert settings.OPENAI_API_KEY is None
