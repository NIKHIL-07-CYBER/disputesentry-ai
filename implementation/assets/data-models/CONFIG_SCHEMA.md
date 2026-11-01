# Configuration Schema and Resolution Rules

This document defines the configuration options for DisputeSentry AI, default values, and environment variable override rules.

---

## 1. Resolution Precedence

Configuration settings are resolved in the following descending order:
1. **Explicit Environment Variables** (prefixed with `DSP_`, e.g., `DSP_PAYPAL_CLIENT_ID`).
2. **Local Environment File** (`.env` in repository root).
3. **Application Config File** (`config.yaml` in repository root).
4. **Pydantic Model Defaults** defined in `app/config.py`.

---

## 2. Pydantic Configuration Model

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class AppConfig(BaseSettings):
    # Environment & Server
    env: str = Field(default="development", description="development, test, or production")
    host: str = Field(default="127.0.0.1", description="Bind host")
    port: int = Field(default=8000, description="Bind port")
    log_level: str = Field(default="INFO", description="DEBUG, INFO, WARNING, ERROR")

    # PayPal API Settings
    paypal_client_id: str = Field(default="sandbox_client_id", description="PayPal OAuth Client ID")
    paypal_client_secret: str = Field(default="sandbox_secret", description="PayPal OAuth Secret")
    paypal_api_base: str = Field(
        default="https://api-m.sandbox.paypal.com",
        description="PayPal API Endpoint Base URL"
    )
    paypal_webhook_id: str = Field(
        default="WH-SANDBOX-12345",
        description="Registered Webhook ID for signature verification"
    )

    # Economic & Policy Thresholds
    high_value_threshold_usd: float = Field(
        default=100.0,
        description="Dispute amount >= threshold requires human approval"
    )
    standard_dispute_fee_usd: float = Field(
        default=15.0,
        description="Standard PayPal dispute fee applied on loss"
    )
    overhead_labor_cost_usd: float = Field(
        default=5.0,
        description="Estimated internal labor/tooling cost to contest a dispute"
    )
    deadline_fail_safe_hours: float = Field(
        default=2.0,
        description="Trigger automatic defensive evidence upload when time <= threshold"
    )

    # AI Reasoning Provider
    ai_provider: str = Field(default="gemini", description="AI reasoning engine provider")
    gemini_api_key: str = Field(default="", description="Google Gemini API key")
    gemini_model_name: str = Field(default="gemini-2.5-flash", description="Target Gemini model")

    # Database
    database_url: str = Field(
        default="sqlite+aiosqlite:///disputesentry.db",
        description="Local SQLite database file path"
    )

    class Config:
        env_prefix = "DSP_"
        env_file = ".env"
        extra = "ignore"
```

---

## 3. Security Restrictions

- The `gemini_api_key` and `paypal_client_secret` must never be logged or rendered in templates.
- If running with `env="test"`, the application bypasses external network calls and binds to local mock fixtures.
