# S01 tests: Verification Test Harness and Fixture Runner

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T01-01` | Fixture directory discovery | Enumerate `catalog/fixtures/` | Exactly 22 subdirectories found (`DSP001` to `DSP022`) |
| `T01-02` | Fixture file structure validation | Inspect each discovered directory | Each contains `good.json`, `bad.json`, and `expected.yaml` |
| `T01-03` | Schema loader test | Validate `catalog/_schema.json` | Valid Draft 2020-12 JSON Schema |
| `T01-04` | Fixture runner assertion engine | Run runner against mock passing fixture | Returns `FixturePassResult(status="PASSED", catalog_id="DSP001")` |

## Positive cases
- All 22 fixture sets load valid JSON/YAML without parser errors.
- Schema validator confirms all `expected.yaml` files have `id` and `outcome`.

## Negative cases
- Missing `good.json` in a fixture directory raises `FixtureNotFoundError`.
- Malformed YAML in `expected.yaml` raises `FixtureSchemaError`.

## Boundary cases
- Empty JSON payload `{}` in `bad.json` is correctly parsed as valid JSON dict.

## Fixtures and golden files used
- `catalog/fixtures/DSP001/` through `catalog/fixtures/DSP022/`
- `catalog/_schema.json`

## Commands to run (exact)
```bash
pytest tests/test_catalog_fixtures.py -v
```

## Coverage target
- 100% of `tests/harness/fixture_runner.py` and `tests/test_catalog_fixtures.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Hardcoding paths with backslashes on Windows; must use `pathlib.Path`.
- Expecting catalog items to pass domain execution before domain code is written; runner in S01 must test fixture integrity and mock dispatch, leaving catalog execution for subsequent stages.
