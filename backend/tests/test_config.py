"""
tests/test_config.py
Verify configuration and Pydantic settings loading.
"""
from uuid import UUID
from app.core.config import Settings


def test_settings_defaults():
    settings = Settings(_env_file=None)
    assert settings.APP_NAME == "Operix Industrial AI Safety Platform"
    assert settings.APP_VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert isinstance(settings.DEFAULT_FACTORY_ID, UUID)
    assert str(settings.DEFAULT_FACTORY_ID) == "aaaaaaaa-0001-0001-0001-000000000001"
    assert settings.ALLOWED_ORIGINS == [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]


def test_settings_cors_parsing():
    settings = Settings(ALLOWED_ORIGINS="http://localhost:3000,http://localhost:8000")
    assert "http://localhost:3000" in settings.ALLOWED_ORIGINS
    assert "http://localhost:8000" in settings.ALLOWED_ORIGINS

    json_settings = Settings(ALLOWED_ORIGINS='["http://localhost:5173"]')
    assert json_settings.ALLOWED_ORIGINS == ["http://localhost:5173"]
