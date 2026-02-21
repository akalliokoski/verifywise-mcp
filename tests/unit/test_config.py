"""Unit tests for the configuration module.

Tests Settings loading from environment variables.
"""

import pytest
from pydantic import ValidationError


def test_settings_loads_defaults(monkeypatch):
    """Settings with required fields should use correct defaults."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "test@example.com")
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "testpass")
    monkeypatch.delenv("VERIFYWISE_BASE_URL", raising=False)
    monkeypatch.delenv("VERIFYWISE_LOG_LEVEL", raising=False)
    monkeypatch.delenv("VERIFYWISE_TRANSPORT", raising=False)
    monkeypatch.delenv("VERIFYWISE_REQUEST_TIMEOUT", raising=False)
    monkeypatch.delenv("VERIFYWISE_MAX_RETRIES", raising=False)

    from verifywise_mcp.config import Settings

    settings = Settings()
    assert settings.base_url == "http://localhost:3000"
    assert settings.email == "test@example.com"
    assert settings.password == "testpass"
    assert settings.log_level == "INFO"
    assert settings.transport == "stdio"
    assert settings.request_timeout == 30.0
    assert settings.max_retries == 3


def test_settings_reads_env_vars(monkeypatch):
    """Settings should read VERIFYWISE_-prefixed environment variables."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "admin@example.com")
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "secret123")
    monkeypatch.setenv("VERIFYWISE_BASE_URL", "http://custom:3000")
    monkeypatch.setenv("VERIFYWISE_LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("VERIFYWISE_TRANSPORT", "http")
    monkeypatch.setenv("VERIFYWISE_REQUEST_TIMEOUT", "60.0")
    monkeypatch.setenv("VERIFYWISE_MAX_RETRIES", "5")

    from verifywise_mcp.config import Settings

    settings = Settings()
    assert settings.base_url == "http://custom:3000"
    assert settings.email == "admin@example.com"
    assert settings.password == "secret123"
    assert settings.log_level == "DEBUG"
    assert settings.transport == "http"
    assert settings.request_timeout == 60.0
    assert settings.max_retries == 5


def test_settings_requires_email(monkeypatch):
    """Settings should raise ValidationError if VERIFYWISE_EMAIL is not set."""
    monkeypatch.delenv("VERIFYWISE_EMAIL", raising=False)
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "pw")

    from verifywise_mcp.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_requires_password(monkeypatch):
    """Settings should raise ValidationError if VERIFYWISE_PASSWORD is not set."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "test@example.com")
    monkeypatch.delenv("VERIFYWISE_PASSWORD", raising=False)

    from verifywise_mcp.config import Settings

    with pytest.raises(ValidationError):
        Settings()


def test_settings_request_timeout_is_float(monkeypatch):
    """Settings.request_timeout should be a float."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "test@example.com")
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "testpass")

    from verifywise_mcp.config import Settings

    settings = Settings()
    assert isinstance(settings.request_timeout, float)


def test_settings_max_retries_is_int(monkeypatch):
    """Settings.max_retries should be an integer."""
    monkeypatch.setenv("VERIFYWISE_EMAIL", "test@example.com")
    monkeypatch.setenv("VERIFYWISE_PASSWORD", "testpass")

    from verifywise_mcp.config import Settings

    settings = Settings()
    assert isinstance(settings.max_retries, int)
