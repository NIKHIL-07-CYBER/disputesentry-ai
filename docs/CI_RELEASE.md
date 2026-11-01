# CI/CD and Release Architecture

This document specifies the continuous integration, testing, packaging, and deployment pipeline design for DisputeSentry AI.

---

## 1. Continuous Integration Pipeline Design

The CI pipeline runs on GitHub Actions on every pull request and push to the default branch. It is structured into four sequential, fail-fast stages:

```
+-----------------------------------------------------------------------------------+
| Stage 1: Fast Static Analysis (< 45s)                                             |
|  - Linting: ruff check app/ tests/                                                |
|  - Formatting: ruff format --check app/ tests/                                    |
|  - Static Typing: mypy --strict app/                                              |
|  - Schema Validation: check-jsonschema --schemafile catalog/_schema.json catalog/*.yaml
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| Stage 2: Unit & Fixture Verification (< 60s)                                      |
|  - Fixture Runner: pytest tests/test_catalog_fixtures.py                          |
|  - Domain Unit Tests: pytest tests/domain/ tests/services/                        |
|  - Code Coverage: pytest --cov=app --cov-fail-under=90                            |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| Stage 3: Mock Contract & Security Matrix (< 90s)                                  |
|  - Python Matrix: [3.11, 3.12, 3.13] across Ubuntu, macOS, Windows               |
|  - API Contract Mocks: respx mock suite against PayPal Disputes v1 schemas        |
|  - Security Audits: pip-audit (CVE detection), bandit -r app/                     |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| Stage 4: Package & Container Build (< 120s)                                       |
|  - Multi-arch Docker build (linux/amd64, linux/arm64)                             |
|  - Container health check: curl -f http://localhost:8000/health                  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Release and Packaging Pipeline

### 2.1 Multi-Architecture Docker Container
- **Base Image**: `python:3.11-slim-bookworm`
- **Exposed Port**: 8000
- **Volumes**:
  - `/data` for SQLite database (`disputesentry.db`) and WAL journals
- **Entrypoint**: `python -m uvicorn app.main:app --host 0.0.0.0 --port 8000`
- **Environment Inputs**:
  - `PAYPAL_MODE`: `sandbox` (default) or `live`
  - `PAYPAL_CLIENT_ID`: PayPal Developer application client ID
  - `PAYPAL_CLIENT_SECRET`: PayPal Developer application secret
  - `PAYPAL_WEBHOOK_ID`: Subscribed webhook ID
  - `GEMINI_API_KEY`: API key for Gemini structured decision engine

### 2.2 Local CLI Distribution
- Packaged as a standard Python wheel (`pyproject.toml` / `pip install -e .`).
- Installs the `disputesentry` executable providing:
  - `disputesentry serve`
  - `disputesentry sync`
  - `disputesentry evaluate`
  - `disputesentry seed`

---

## 3. Demo and Hackathon Deployment Strategy

To satisfy hackathon submission criteria [18][42]:
1. **Public Hosted Demo**:
   - Deployed on a lightweight cloud container host (e.g., Fly.io or Render free tier).
   - Pre-seeded with realistic merchant order and tracking data.
   - Connected to a live PayPal Sandbox business account.
2. **Local Zero-Ops Run Script**:
   - Judges can clone the repository and run:
     ```bash
     python -m venv venv
     source venv/bin/activate  # or .\venv\Scripts\Activate.ps1
     pip install -r requirements.txt
     python -m disputesentry seed
     python -m disputesentry serve
     ```
   - Instantly opens the dashboard at `http://localhost:8000` with pre-loaded disputes ready for evaluation and sandbox execution.
