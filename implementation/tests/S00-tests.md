# S00 tests: Scaffolding and Tooling

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T00-01` | Config loader default values | Load `AppConfig()` with empty environment | `config.env == "development"`, `config.port == 8000`, `config.high_value_threshold_usd == 100.0` |
| `T00-02` | Config env override | `os.environ["DSP_PORT"] = "9000"` | `config.port == 9000` |
| `T00-03` | FastApi health endpoint test | `GET /health` | HTTP 200 `{"status": "healthy", "service": "disputesentry-ai"}` |

## Positive cases
- `AppConfig` initializes and parses `config.yaml` cleanly.
- `GET /health` returns JSON status and version string.

## Negative cases
- Invalid port string in environment (`DSP_PORT="abc"`) raises Pydantic `ValidationError`.
- Non-existent config file path falls back gracefully to defaults.

## Boundary cases
- Zero or negative timeout configuration values trigger validation error.

## Fixtures and golden files used
- `config.yaml`
- `tests/conftest.py`

## Commands to run (exact)
```bash
pytest tests/unit/test_config.py
ruff check app/ tests/
mypy --strict app/
```

## Coverage target
- 100% line coverage of `app/config.py` and `app/main.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Hardcoding secrets in `config.yaml`.
- Forgetting `extra = "ignore"` in Pydantic `Config`, causing environment clashes.
