"""Configuration management for DisputeSentry AI using Pydantic Settings."""

from pathlib import Path
from typing import Any, ClassVar

from pydantic import Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class AppConfig(BaseSettings):
    """Application configuration schema and resolution hierarchy."""

    _custom_yaml_path: ClassVar[str | None] = None

    # Environment & Server
    env: str = Field(default="development", description="development, test, or production")
    host: str = Field(default="127.0.0.1", description="Bind host")
    port: int = Field(default=8000, gt=0, le=65535, description="Bind port")
    log_level: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR")

    # PayPal API Settings
    paypal_client_id: str = Field(
        default="sandbox_client_id", description="PayPal OAuth Client ID"
    )
    paypal_client_secret: str = Field(
        default="sandbox_secret", description="PayPal OAuth Secret"
    )
    paypal_api_base: str = Field(
        default="https://api-m.sandbox.paypal.com",
        description="PayPal API Endpoint Base URL",
    )
    paypal_webhook_id: str = Field(
        default="WH-SANDBOX-12345",
        description="Registered Webhook ID for signature verification",
    )

    # Economic & Policy Thresholds
    high_value_threshold_usd: float = Field(
        default=100.0,
        ge=0.0,
        description="Dispute amount >= threshold requires human approval",
    )
    standard_dispute_fee_usd: float = Field(
        default=15.0,
        ge=0.0,
        description="Standard PayPal dispute fee applied on loss",
    )
    overhead_labor_cost_usd: float = Field(
        default=5.0,
        ge=0.0,
        description="Estimated internal labor/tooling cost to contest a dispute",
    )
    deadline_fail_safe_hours: float = Field(
        default=2.0,
        gt=0.0,
        description="Trigger automatic defensive evidence upload when time <= threshold",
    )

    # AI Reasoning Provider
    ai_provider: str = Field(default="gemini", description="AI reasoning engine provider")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model_name: str = Field(default="gemini-2.5-flash", description="Target Gemini model")
    timeout_seconds: float = Field(
        default=10.0,
        gt=0.0,
        description="Timeout in seconds for external service and AI calls",
    )

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///disputesentry.db",
        description="Local SQLite database file path",
    )

    model_config = SettingsConfigDict(
        env_prefix="DSP_",
        env_file=".env",
        extra="ignore",
        yaml_file="config.yaml",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Customise settings sources to prioritize Env > Dotenv > YAML > Defaults."""
        yaml_path: str | None = getattr(settings_cls, "_custom_yaml_path", None)
        if yaml_path is None:
            config_val = settings_cls.model_config.get("yaml_file")
            yaml_path = str(config_val) if config_val is not None else None

        yaml_source = (
            YamlConfigSettingsSource(settings_cls, yaml_file=Path(yaml_path))
            if yaml_path
            else YamlConfigSettingsSource(settings_cls)
        )

        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_source,
            file_secret_settings,
        )


def get_config(yaml_file: str | Path | None = None, **kwargs: Any) -> AppConfig:
    """Load and return an AppConfig instance.

    Args:
        yaml_file: Optional path to a YAML configuration file.
        **kwargs: Explicit keyword arguments overriding config values.

    Returns:
        AppConfig: Resolved configuration model.
    """
    if yaml_file is not None:
        prev_custom = AppConfig._custom_yaml_path
        try:
            AppConfig._custom_yaml_path = str(yaml_file)
            return AppConfig(**kwargs)
        finally:
            AppConfig._custom_yaml_path = prev_custom

    return AppConfig(**kwargs)


load_config = get_config
