import pytest
from pydantic import ValidationError

from text_to_sql_agent.app.core.config import (
    PACKAGE_ENV_FILE,
    PROJECT_ROOT_ENV_FILE,
    Settings,
)


def test_settings_env_file_is_anchored_to_project_root():
    assert PROJECT_ROOT_ENV_FILE.is_absolute()
    assert PROJECT_ROOT_ENV_FILE.name == ".env"
    assert PROJECT_ROOT_ENV_FILE.parent.name == "text-to-sql-agent"
    assert Settings.model_config["env_file"] == (
        PACKAGE_ENV_FILE,
        PROJECT_ROOT_ENV_FILE,
    )


def test_settings_load_database_url_without_openai_api_key(
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = "postgresql+asyncpg://user:password@localhost/example"
    query_database_url = "******localhost/analytics"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("TEXT_TO_SQL_DATABASE_URL", query_database_url)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == database_url
    assert settings.TEXT_TO_SQL_DATABASE_URL == query_database_url
    assert settings.OPENAI_API_KEY is None


def test_query_database_url_is_required(
    monkeypatch: pytest.MonkeyPatch,
):
    database_url = "postgresql+asyncpg://app/app_db"
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.delenv("TEXT_TO_SQL_DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="TEXT_TO_SQL_DATABASE_URL"):
        Settings(_env_file=None)


def test_query_database_url_has_its_own_setting(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://app/app_db")
    monkeypatch.setenv("TEXT_TO_SQL_DATABASE_URL", "sqlite:///analytics.db")

    settings = Settings(_env_file=None)

    assert settings.DATABASE_URL == "postgresql+asyncpg://app/app_db"
    assert settings.TEXT_TO_SQL_DATABASE_URL == "sqlite:///analytics.db"
