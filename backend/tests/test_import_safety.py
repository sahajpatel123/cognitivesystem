import importlib
import os


def test_config_imports():
    import backend.app.config  # noqa: F401


def test_main_imports():
    from backend.app.main import app  # noqa: F401


def test_pydantic_settings_imports():
    from pydantic_settings import BaseSettings  # noqa: F401


def test_settings_has_cors_origins():
    from backend.app.config import settings

    assert hasattr(settings, "cors_origins")
    assert isinstance(settings.cors_origins, list)


def test_cors_parsing_csv(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "http://a.com, http://b.com")
    import backend.app.config as config

    importlib.reload(config)
    assert config.settings.cors_origins == ["http://a.com", "http://b.com"]
