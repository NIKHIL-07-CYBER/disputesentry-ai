# Sample Configuration Files

This document provides sample valid configuration files for development, testing, and production environments.

---

## 1. Development Configuration (`config.yaml`)

```yaml
env: development
host: 127.0.0.1
port: 8000
log_level: DEBUG

paypal_client_id: "SANDBOX_MOCK_CLIENT_ID"
paypal_client_secret: "SANDBOX_MOCK_CLIENT_SECRET"
paypal_api_base: "https://api-m.sandbox.paypal.com"
paypal_webhook_id: "WH-DEV-TEST-001"

high_value_threshold_usd: 100.0
standard_dispute_fee_usd: 15.0
overhead_labor_cost_usd: 5.0
deadline_fail_safe_hours: 2.0

ai_provider: "gemini"
gemini_api_key: "MOCK_DEV_KEY"
gemini_model_name: "gemini-2.5-flash"

database_url: "sqlite+aiosqlite:///disputesentry_dev.db"
```

---

## 2. Test Environment (`.env.test`)

```env
DSP_ENV=test
DSP_LOG_LEVEL=WARNING
DSP_PAYPAL_CLIENT_ID=test_id
DSP_PAYPAL_CLIENT_SECRET=test_secret
DSP_DATABASE_URL=sqlite+aiosqlite:///:memory:
DSP_GEMINI_API_KEY=test_offline_key
```
