"""Unit tests for configuration loader and health endpoint (Stage S00)."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
from pydantic import ValidationError

from app.config import AppConfig, get_config


def test_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """T00-01: Verify default configuration values with an empty environment."""
    for key in list(os.environ.keys()):
        if key.startswith("DSP_"):
            monkeypatch.delenv(key, raising=False)

    config = get_config(yaml_file="non_existent_defaults_test.yaml")
    assert config.env == "development"
    assert config.host == "127.0.0.1"
    assert config.port == 8000
    assert config.log_level == "INFO"
    assert config.high_value_threshold_usd == 100.0
    assert config.standard_dispute_fee_usd == 15.0
    assert config.overhead_labor_cost_usd == 5.0
    assert config.deadline_fail_safe_hours == 2.0
    assert config.ai_provider == "gemini"
    assert config.gemini_model_name == "gemini-2.5-flash"
    assert config.timeout_seconds == 10.0


def test_config_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    """T00-02: Verify environment variables override config values with proper type-casting."""
    monkeypatch.setenv("DSP_PORT", "9000")
    monkeypatch.setenv("DSP_ENV", "production")
    monkeypatch.setenv("DSP_HIGH_VALUE_THRESHOLD_USD", "250.50")
    monkeypatch.setenv("DSP_STANDARD_DISPUTE_FEE_USD", "20.0")

    config = AppConfig()
    assert config.port == 9000
    assert isinstance(config.port, int)
    assert config.env == "production"
    assert config.high_value_threshold_usd == 250.50
    assert isinstance(config.high_value_threshold_usd, float)
    assert config.standard_dispute_fee_usd == 20.0
    assert isinstance(config.standard_dispute_fee_usd, float)


def test_health_endpoint_sync(client: TestClient) -> None:
    """T00-03: Verify GET /health endpoint returns 200 and expected payload via sync client."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "disputesentry-ai"
    assert data["version"] == "0.1.0"


async def test_health_endpoint_async(async_client: AsyncClient) -> None:
    """T00-03: Verify GET /health endpoint returns 200 and expected payload via async client."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "disputesentry-ai"
    assert data["version"] == "0.1.0"


def test_config_from_yaml(tmp_path: Path) -> None:
    """Positive case: verify loading values from a valid YAML configuration file."""
    yaml_file = tmp_path / "custom_config.yaml"
    yaml_file.write_text(
        """
env: staging
port: 8080
log_level: WARNING
high_value_threshold_usd: 150.0
timeout_seconds: 15.0
"""
    )
    config = get_config(yaml_file=yaml_file)
    assert config.env == "staging"
    assert config.port == 8080
    assert config.log_level == "WARNING"
    assert config.high_value_threshold_usd == 150.0
    assert config.timeout_seconds == 15.0


def test_invalid_port_env_raises_validation_error(monkeypatch: pytest.MonkeyPatch) -> None:
    """Negative case: verify invalid port string in environment raises ValidationError."""
    monkeypatch.setenv("DSP_PORT", "abc")
    with pytest.raises(ValidationError):
        AppConfig()


def test_non_existent_config_file_graceful_fallback() -> None:
    """Negative case: verify missing config file path falls back gracefully to defaults."""
    config = get_config(yaml_file=Path("non_existent_never_file.yaml"))
    assert config.port == 8000
    assert config.env == "development"


def test_timeout_and_port_boundary_validation() -> None:
    """Boundary case: verify non-positive timeout and invalid port values trigger
    ValidationError.
    """
    with pytest.raises(ValidationError):
        AppConfig(timeout_seconds=0.0)

    with pytest.raises(ValidationError):
        AppConfig(timeout_seconds=-5.0)

    with pytest.raises(ValidationError):
        AppConfig(deadline_fail_safe_hours=0.0)

    with pytest.raises(ValidationError):
        AppConfig(port=0)

    with pytest.raises(ValidationError):
        AppConfig(port=70000)
