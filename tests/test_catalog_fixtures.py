"""Behavior catalog fixture discovery, schema validation, and test harness execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from tests.harness.fixture_runner import (
    CatalogFixtureRunner,
    FixturePassResult,
    FixtureResult,
)
from tests.harness.schema_validator import (
    FixtureNotFoundError,
    FixtureSchemaError,
    validate_catalog_schema_file,
    validate_expected_yaml_content,
    validate_fixture_directory_structure,
)

CATALOG_FIXTURES_DIR = Path(__file__).resolve().parent.parent / "catalog" / "fixtures"
CATALOG_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "catalog" / "_schema.json"

EXPECTED_CATALOG_IDS = [f"DSP{i:03d}" for i in range(1, 23)]


@pytest.fixture
def fixtures_dir() -> Path:
    """Fixture providing the path to catalog fixtures directory."""
    return CATALOG_FIXTURES_DIR


@pytest.fixture
def runner(fixtures_dir: Path) -> CatalogFixtureRunner:
    """Fixture providing an initialized CatalogFixtureRunner instance."""
    return CatalogFixtureRunner(fixtures_dir=fixtures_dir)


def test_t01_01_fixture_directory_discovery(runner: CatalogFixtureRunner) -> None:
    """T01-01: Verify discovery finds exactly 22 subdirectories (DSP001 through DSP022)."""
    discovered = runner.discover_fixtures()
    assert len(discovered) == 22, f"Expected 22 fixtures, found {len(discovered)}: {discovered}"
    assert discovered == EXPECTED_CATALOG_IDS, f"Discovered mismatch: {discovered}"


def test_t01_02_fixture_file_structure_validation(
    runner: CatalogFixtureRunner,
    fixtures_dir: Path,
) -> None:
    """T01-02: Verify every discovered directory contains good.json, bad.json, and expected.yaml."""
    discovered = runner.discover_fixtures()
    for catalog_id in discovered:
        target_dir = fixtures_dir / catalog_id
        good_file = target_dir / "good.json"
        bad_file = target_dir / "bad.json"
        expected_file = target_dir / "expected.yaml"

        assert good_file.is_file(), f"Missing good.json in {target_dir}"
        assert bad_file.is_file(), f"Missing bad.json in {target_dir}"
        assert expected_file.is_file(), f"Missing expected.yaml in {target_dir}"


def test_t01_03_schema_loader_test() -> None:
    """T01-03: Validate that catalog/_schema.json is a valid Draft 2020-12 JSON Schema."""
    schema = validate_catalog_schema_file(CATALOG_SCHEMA_PATH)
    assert isinstance(schema, dict)
    assert schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"
    assert schema.get("title") == "DisputeSentryCatalogItem"


def test_t01_04_fixture_runner_assertion_engine(runner: CatalogFixtureRunner) -> None:
    """T01-04: Verify runner against default baseline and dynamic custom mock handlers."""
    # Test default baseline execution (S01 fixture integrity and schema pass)
    result = runner.execute_oracle_check("DSP001")
    assert isinstance(result, FixtureResult)
    assert result.catalog_id == "DSP001"
    assert result.status == "PASSED"

    # Test dynamic mock handler dispatch
    mock_runner = CatalogFixtureRunner(fixtures_dir=runner.fixtures_dir)

    def mock_passing_handler(
        good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
    ) -> FixtureResult:
        assert isinstance(good, dict)
        assert isinstance(bad, dict)
        assert isinstance(expected, dict)
        return FixturePassResult(
            catalog_id="DSP001",
            status="PASSED",
            details="Mock handler successfully verified DSP001 behavior",
        )

    mock_runner.register_handler("DSP001", mock_passing_handler)
    mock_result = mock_runner.execute_oracle_check("DSP001")
    assert isinstance(mock_result, FixturePassResult)
    assert mock_result.catalog_id == "DSP001"
    assert mock_result.status == "PASSED"
    assert "Mock handler successfully verified" in mock_result.details


def test_positive_fixture_loading_and_parsing(runner: CatalogFixtureRunner) -> None:
    """Verify all 22 fixture sets load valid JSON/YAML without parser errors."""
    for catalog_id in EXPECTED_CATALOG_IDS:
        good, bad, expected = runner.load_fixture(catalog_id)
        assert isinstance(good, dict), f"good.json for {catalog_id} must be dict"
        assert isinstance(bad, dict), f"bad.json for {catalog_id} must be dict"
        assert isinstance(expected, dict), f"expected.yaml for {catalog_id} must be dict"
        assert expected.get("id") == catalog_id


def test_negative_missing_good_json_raises_fixture_not_found(tmp_path: Path) -> None:
    """Negative case: Missing good.json in a fixture directory raises FixtureNotFoundError."""
    fixture_dir = tmp_path / "DSP001"
    fixture_dir.mkdir()
    (fixture_dir / "bad.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "expected.yaml").write_text(
        "id: DSP001\ngood: {}\nbad: {}\n", encoding="utf-8"
    )

    with pytest.raises(FixtureNotFoundError, match="Required fixture file missing: good.json"):
        validate_fixture_directory_structure(fixture_dir)


def test_negative_missing_bad_json_raises_fixture_not_found(tmp_path: Path) -> None:
    """Negative case: Missing bad.json in a fixture directory raises FixtureNotFoundError."""
    fixture_dir = tmp_path / "DSP001"
    fixture_dir.mkdir()
    (fixture_dir / "good.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "expected.yaml").write_text(
        "id: DSP001\ngood: {}\nbad: {}\n", encoding="utf-8"
    )

    with pytest.raises(FixtureNotFoundError, match="Required fixture file missing: bad.json"):
        validate_fixture_directory_structure(fixture_dir)


def test_negative_missing_expected_yaml_raises_fixture_not_found(tmp_path: Path) -> None:
    """Negative case: Missing expected.yaml raises FixtureNotFoundError."""
    fixture_dir = tmp_path / "DSP001"
    fixture_dir.mkdir()
    (fixture_dir / "good.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "bad.json").write_text("{}", encoding="utf-8")

    with pytest.raises(FixtureNotFoundError, match="Required fixture file missing: expected.yaml"):
        validate_fixture_directory_structure(fixture_dir)


def test_negative_malformed_yaml_raises_fixture_schema_error(tmp_path: Path) -> None:
    """Negative case: Malformed YAML in expected.yaml raises FixtureSchemaError."""
    fixture_dir = tmp_path / "DSP001"
    fixture_dir.mkdir()
    (fixture_dir / "good.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "bad.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "expected.yaml").write_text("id: DSP001\nmalformed: [unclosed", encoding="utf-8")

    with pytest.raises(FixtureSchemaError, match="Malformed YAML"):
        validate_fixture_directory_structure(fixture_dir)


def test_negative_non_existent_fixture_directory_raises(runner: CatalogFixtureRunner) -> None:
    """Negative case: Querying a non-existent catalog ID raises FixtureNotFoundError."""
    with pytest.raises(FixtureNotFoundError, match="Fixture directory not found for DSP999"):
        runner.load_fixture("DSP999")


def test_negative_schema_loader_nonexistent_file(tmp_path: Path) -> None:
    """Negative case: Attempting to load missing schema file raises FixtureNotFoundError."""
    missing_file = tmp_path / "missing_schema.json"
    with pytest.raises(FixtureNotFoundError, match="Catalog schema file not found"):
        validate_catalog_schema_file(missing_file)


def test_negative_invalid_expected_yaml_structure() -> None:
    """Negative case: expected.yaml missing id or structural blocks raises FixtureSchemaError."""
    with pytest.raises(FixtureSchemaError, match="missing mandatory 'id'"):
        validate_expected_yaml_content({"good": {}, "bad": {}})

    with pytest.raises(FixtureSchemaError, match="Invalid catalog ID"):
        validate_expected_yaml_content({"id": "INVALID", "good": {}, "bad": {}})

    with pytest.raises(FixtureSchemaError, match="must declare either 'good' and 'bad'"):
        validate_expected_yaml_content({"id": "DSP001", "other": "data"})


def test_boundary_empty_json_dict_parsed_correctly(tmp_path: Path) -> None:
    """Boundary case: Empty JSON payload '{}' in bad.json is correctly parsed as valid dict."""
    fixture_dir = tmp_path / "DSP001"
    fixture_dir.mkdir()
    (fixture_dir / "good.json").write_text('{"key": "value"}', encoding="utf-8")
    (fixture_dir / "bad.json").write_text("{}", encoding="utf-8")
    (fixture_dir / "expected.yaml").write_text(
        "id: DSP001\ngood: {}\nbad: {}\n", encoding="utf-8"
    )

    good, bad, expected = validate_fixture_directory_structure(fixture_dir)
    assert good == {"key": "value"}
    assert bad == {}
    assert expected["id"] == "DSP001"


def test_handler_exception_returns_failure(runner: CatalogFixtureRunner) -> None:
    """Verify that an unhandled exception inside a domain handler returns FixtureResult FAILED."""
    runner_instance = CatalogFixtureRunner(fixtures_dir=runner.fixtures_dir)

    def failing_handler(
        good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
    ) -> FixtureResult:
        raise RuntimeError("Simulated domain handler explosion")

    runner_instance.register_handler("DSP001", failing_handler)
    res = runner_instance.execute_oracle_check("DSP001")
    assert res.status == "FAILED"
    assert "Simulated domain handler explosion" in res.details


@pytest.mark.parametrize("catalog_id", EXPECTED_CATALOG_IDS)
def test_all_catalog_fixtures_pass_oracle_integrity_check(
    catalog_id: str,
    runner: CatalogFixtureRunner,
) -> None:
    """Parameterized test: Verify all 22 catalog item fixtures pass oracle checks with 100% rate."""
    result = runner.execute_oracle_check(catalog_id)
    assert result.status == "PASSED", f"Oracle check failed for {catalog_id}: {result.details}"
    assert result.catalog_id == catalog_id
