# S01 Verification Test Harness and Fixture Runner

## 1 Goal and outcome
Build an automated fixture runner (`tests/test_catalog_fixtures.py` and `tests/harness/fixture_runner.py`) that loads all 22 behavior catalog item fixtures (`catalog/fixtures/DSP001` through `DSP022`), validates their schema conformance, and executes mock assertion passes without modifying fixture files.

## 2 Entry conditions
- Stage S00 complete (`pytest` and `ruff` passing).
- Catalog fixture directories present under `catalog/fixtures/`.

## 3 Read first
1. `docs/VERIFICATION.md`
2. `catalog/_schema.json`
3. `implementation/tests/FIXTURE_CONVENTIONS.md`
4. `implementation/tests/ITEM_TEST_RECIPE.md`
5. `implementation/tests/S01-tests.md`

## 4 Files to create or modify
- `tests/harness/__init__.py`
- `tests/harness/fixture_runner.py`
- `tests/harness/schema_validator.py`
- `tests/test_catalog_fixtures.py`

## 5 Forbidden changes
- Never modify files inside `catalog/fixtures/` or `catalog/_schema.json`.
- Never hardcode OS-specific path separators.

## 6 Interfaces and signatures
```python
from pathlib import Path
from pydantic import BaseModel

class FixtureResult(BaseModel):
    catalog_id: str
    status: str  # "PASSED", "FAILED", "SKIPPED"
    details: str

class CatalogFixtureRunner:
    def __init__(self, fixtures_dir: Path): ...
    def discover_fixtures(self) -> list[str]: ...
    def load_fixture(self, catalog_id: str) -> tuple[dict, dict, dict]: ...
    def execute_oracle_check(self, catalog_id: str) -> FixtureResult: ...
```

## 7 Step-by-step instructions
1. Create `tests/harness/schema_validator.py` to validate `expected.yaml` structure.
2. Implement `tests/harness/fixture_runner.py` capable of scanning `catalog/fixtures/` and loading `good.json`, `bad.json`, `expected.yaml`.
3. Implement `tests/test_catalog_fixtures.py` containing parameterized pytest cases iterating over all 22 catalog IDs.
4. Verify that missing fixture files trigger explicit test failures.
5. In S01, the oracle checks verify fixture integrity and schema compliance; domain execution will be plugged in as stages implement respective catalog IDs.

## 8 Edge cases
- Windows path separators (`\` vs `/`) handled using `pathlib.Path`.
- Fixture directories containing hidden files or non-JSON artifacts are filtered out.

## 9 Out of scope
- Implementation of domain logic (handled in stages S02 through S09).

## 10 Tests
Follow instructions in `implementation/tests/S01-tests.md`.

## 11 Exit criteria
- `pytest tests/test_catalog_fixtures.py` runs and verifies all 22 catalog fixture sets with 100% pass rate.
- `ruff check tests/harness/ tests/test_catalog_fixtures.py` passes with zero errors.

## 12 Commit message
`test(harness): implement dynamic catalog fixture runner and schema validation suite`

## 13 Failure and rollback handling
If fixture parsing fails, inspect encoding (must be UTF-8) and ensure standard PyYAML parser loads `expected.yaml` cleanly.

## 14 Common AI-agent pitfalls for this stage
- Trying to execute domain modules before they exist; keep the runner modular so execution logic can be wired dynamically.
- Modifying fixture files to make tests pass.

## 15 Handoff notes for the next stage
Provides the verification harness used by S02 to prove `DSP001` - `DSP004`.
