# Pinned Dependencies and Selection Justifications

All dependencies must be strictly pinned in `requirements.txt` to eliminate transitive build breakage and ensure reproducible local execution.

---

## 1. Runtime Dependencies

| Package | Pinned Version | Justification |
|---|---|---|
| `fastapi` | `0.115.0` | Modern, high-performance async web framework providing automatic OpenAPI schema generation and typed request dependency injection. |
| `uvicorn` | `0.32.0` | ASGI server running the FastAPI application with high-throughput async event loops. |
| `pydantic` | `2.9.2` | Core data validation and serialization. Compiles JSON schemas for structured LLM reasoning and internal type enforcement. |
| `pydantic-settings` | `2.5.2` | Environment variable and configuration file management with strict type casting. |
| `httpx` | `0.27.2` | Fully async HTTP client supporting connection pooling, timeout budgets, and multipart payload streaming for PayPal API v1. |
| `cryptography` | `43.0.1` | High-performance cryptographic library used to verify PayPal X.509 certificates and compute RSA-SHA256 signatures over incoming webhooks. |
| `aiosqlite` | `0.20.0` | Asynchronous SQLite interface providing non-blocking local relational storage with WAL mode support. |
| `jinja2` | `3.1.4` | Server-side templating engine for rendering the merchant operator web dashboard without external frontend build tools. |
| `pyyaml` | `6.0.2` | YAML parser for loading catalog item specifications (`catalog/*.yaml`) and application configuration (`config.yaml`). |
| `google-genai` | `0.1.1` | Google GenAI SDK for Gemini 2.5 / 1.5 Flash structured decision reasoning with Pydantic JSON schema constraints. |

---

## 2. Test and Development Dependencies

| Package | Pinned Version | Justification |
|---|---|---|
| `pytest` | `8.3.3` | Test execution harness and assertion engine. |
| `pytest-asyncio` | `0.24.0` | Enables native async test functions for testing FastAPI routes and async services. |
| `pytest-mock` | `3.14.0` | Pytest fixture wrapper around `unittest.mock` for deterministic test isolation. |
| `respx` | `0.21.1` | Mocking and contract testing library for `httpx` requests, eliminating external network dependencies during test runs. |
| `ruff` | `0.6.9` | Ultra-fast linter and code formatter ensuring consistent code standards across stages. |
| `mypy` | `1.11.2` | Static type checker enforcing zero implicit `Any` types across the codebase. |

---

## 3. Dependency Policy

1. **Zero New Runtime Dependencies:** Implementation stages (`S00` to `S11`) are strictly forbidden from introducing third-party packages not listed in this document without an approved spec-fix ADR.
2. **Local Reproducibility:** No external cloud database (Postgres, Redis) or Docker runtime is required for unit or integration testing; all tests must execute in standard Python virtualenv in < 3 seconds.
