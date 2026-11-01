# S00 Scaffolding and Tooling

## 1 Goal and outcome
Establish the Python 3.11+ workspace, pinned dependencies in `requirements.txt`, linter/formatter configurations in `pyproject.toml`, application settings loader (`app/config.py`), base FastAPI application entrypoint with health check (`app/main.py`), and pytest conftest infrastructure. All tooling checks pass cleanly.

## 2 Entry conditions
- Foundation documents exist (`docs/SPEC.md`, `docs/ARCHITECTURE.md`, `docs/adr/ADR-001-language-and-stack.md`).
- Python 3.11+ environment available.

## 3 Read first
1. `docs/adr/ADR-001-language-and-stack.md`
2. `implementation/assets/architecture/REPO_LAYOUT.md`
3. `implementation/assets/architecture/DEPENDENCIES.md`
4. `implementation/assets/architecture/CODING_STANDARDS.md`
5. `implementation/assets/data-models/CONFIG_SCHEMA.md`
6. `implementation/tests/S00-tests.md`

## 4 Files to create or modify
- `pyproject.toml`
- `requirements.txt`
- `.gitignore`
- `config.yaml`
- `app/__init__.py`
- `app/config.py`
- `app/main.py`
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/unit/test_config.py`

## 5 Forbidden changes
- Never edit files in `catalog/` or `docs/`.
- Never install or add dependencies not listed in `implementation/assets/architecture/DEPENDENCIES.md`.
- Do not implement database logic or external API clients in this stage.

## 6 Interfaces and signatures
```python
from pydantic_settings import BaseSettings
from pydantic import Field
from fastapi import FastAPI

class AppConfig(BaseSettings):
    env: str = Field(default="development")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=8000)
    log_level: str = Field(default="INFO")
    high_value_threshold_usd: float = Field(default=100.0)
    # ... remaining fields per CONFIG_SCHEMA.md

def create_app() -> FastAPI:
    """Instantiate and configure FastAPI application."""
```

## 7 Step-by-step instructions
1. Create `requirements.txt` with exact pinned versions from `assets/architecture/DEPENDENCIES.md`.
2. Create `pyproject.toml` with `ruff` (line length 100) and `mypy` strict configurations.
3. Create `.gitignore` ignoring virtualenvs, `__pycache__`, `.pytest_cache`, `.mypy_cache`, and SQLite `.db` files.
4. Create `config.yaml` with development defaults per `assets/examples/SAMPLE_CONFIGS.md`.
5. Implement `app/config.py` with `AppConfig` inheriting from `BaseSettings`.
6. Implement `tests/unit/test_config.py` and run tests (ensure failure before app code, then pass).
7. Implement `app/main.py` with `create_app()` providing `GET /health` returning `{"status": "healthy", "service": "disputesentry-ai"}`.
8. Create `tests/conftest.py` setting up async test client fixtures.

## 8 Edge cases
- Environment variables overriding YAML config values must type-cast integers and floats properly.
- Missing `.env` file should not raise file-not-found errors.

## 9 Out of scope
- Database connections or migrations (deferred to S03).
- PayPal API authentication or webhook verification (deferred to S02/S04).

## 10 Tests
Follow instructions and test cases in `implementation/tests/S00-tests.md`.

## 11 Exit criteria
- `pytest tests/unit/test_config.py` passes 100%.
- `ruff check app/ tests/` outputs zero errors.
- `mypy --strict app/` outputs zero errors.

## 12 Commit message
`chore(scaffold): initialize python 3.11 workspace, dependencies, config and health check`

## 13 Failure and rollback handling
If dependency installation or configuration loading fails, verify virtualenv version and ensure no conflicting environment variables are set.

## 14 Common AI-agent pitfalls for this stage
- Omitting `extra = "ignore"` in Pydantic `Config`, causing crashes when unexpected system environment variables exist.
- Adding unpinned packages or newer major versions.

## 15 Handoff notes for the next stage
Provides `app/config.py` and pytest test execution harness for S01 (Verification Test Harness).
