# S11 tests: Hardening, Sandbox End-to-End Validation & Release

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T11-01` | Full catalog fixture suite runner | Execute dynamic runner across all 22 catalog items | 22/22 items report `PASS` with zero failures |
| `T11-02` | Docker container build & boot | Build Docker image and run container | Container starts within 5s, responds HTTP 200 to `GET /health` |
| `T11-03` | PayPal Sandbox end-to-end integration | Execute test against sandbox API with mock/test credentials | Complete token acquisition, dispute fetch, and evidence test pass |
| `T11-04` | Zero PAN leak audit | Search all log outputs and SQLite DB after full test run | Zero unmasked Luhn-valid card numbers found |

## Positive cases
- Container image starts cleanly in standalone execution without external volumes.
- README run instructions execute from clean checkout without missing dependencies.

## Negative cases
- Running without credentials in production mode halts with actionable error message.

## Boundary cases
- Full test suite execution finishes in $< 5.0\text{ seconds}$ in local virtual environment.

## Fixtures and golden files used
- All 22 catalog item fixtures (`catalog/fixtures/DSP001/` to `DSP022/`)
- `Dockerfile`
- `README.md`

## Commands to run (exact)
```bash
pytest --cov=app --cov-report=term-missing tests/
ruff check app/ tests/
mypy --strict app/
```

## Coverage target
- 90%+ total project line coverage.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Hardcoding local development file paths in Dockerfile or README.
- Shipping debug endpoints or unauthenticated test harnesses into production routes.
