"""Schema validation utilities for behavior catalog fixtures and expected definitions."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import yaml
from jsonschema.validators import Draft202012Validator  # type: ignore[import-untyped]


class FixtureError(Exception):
    """Base exception for fixture verification errors."""


class FixtureNotFoundError(FixtureError, FileNotFoundError):
    """Raised when an expected fixture directory or file is missing."""


class FixtureSchemaError(FixtureError, ValueError):
    """Raised when a fixture payload or expected.yaml fails schema validation."""


ID_PATTERN = re.compile(r"^DSP[0-9]{3}$")


def validate_catalog_schema_file(schema_path: Path) -> dict[str, Any]:
    """Validate that catalog/_schema.json exists and conforms to Draft 2020-12.

    Args:
        schema_path: Path to the JSON schema file.

    Returns:
        The loaded and validated schema as a dictionary.

    Raises:
        FixtureNotFoundError: If the schema file does not exist.
        FixtureSchemaError: If the schema file is malformed JSON or invalid JSON schema.
    """
    if not schema_path.is_file():
        raise FixtureNotFoundError(f"Catalog schema file not found at: {schema_path}")

    try:
        with open(schema_path, encoding="utf-8") as f:
            schema_data: Any = json.load(f)
    except Exception as exc:
        raise FixtureSchemaError(
            f"Failed to parse catalog schema JSON at {schema_path}: {exc}"
        ) from exc

    if not isinstance(schema_data, dict):
        raise FixtureSchemaError(
            f"Catalog schema at {schema_path} must be a JSON object, got {type(schema_data)}"
        )

    try:
        Draft202012Validator.check_schema(schema_data)
    except Exception as exc:
        raise FixtureSchemaError(
            f"Schema at {schema_path} is not valid Draft 2020-12: {exc}"
        ) from exc

    return schema_data


def validate_expected_yaml_content(
    content: str | dict[str, Any],
    require_outcome: bool = False,
) -> dict[str, Any]:
    """Validate the parsed or raw content of expected.yaml.

    Args:
        content: Raw YAML string or pre-parsed dictionary.
        require_outcome: If True, asserts an outcome field is present (top-level or in good).

    Returns:
        The validated dictionary.

    Raises:
        FixtureSchemaError: If validation fails.
    """
    if isinstance(content, str):
        try:
            parsed: Any = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            raise FixtureSchemaError(f"Malformed YAML in expected.yaml: {exc}") from exc
    elif isinstance(content, dict):
        parsed = content
    else:
        raise FixtureSchemaError(f"Expected dict or string for expected.yaml, got {type(content)}")

    if not isinstance(parsed, dict):
        raise FixtureSchemaError(
            f"expected.yaml must define a top-level dictionary, got {type(parsed)}"
        )

    if "id" not in parsed:
        raise FixtureSchemaError("expected.yaml is missing mandatory 'id' field")

    catalog_id = parsed["id"]
    if not isinstance(catalog_id, str) or not ID_PATTERN.match(catalog_id):
        raise FixtureSchemaError(
            f"Invalid catalog ID '{catalog_id}' in expected.yaml; must match ^DSP[0-9]{{3}}$"
        )

    has_branches = "good" in parsed and "bad" in parsed
    has_outcome = "outcome" in parsed

    if not (has_branches or has_outcome):
        raise FixtureSchemaError(
            f"expected.yaml for {catalog_id} must declare either 'good' and 'bad' blocks "
            "or a top-level 'outcome'"
        )

    if "good" in parsed and not isinstance(parsed["good"], dict):
        raise FixtureSchemaError(
            f"'good' block in expected.yaml for {catalog_id} must be a dictionary"
        )

    if "bad" in parsed and not isinstance(parsed["bad"], dict):
        raise FixtureSchemaError(
            f"'bad' block in expected.yaml for {catalog_id} must be a dictionary"
        )

    if require_outcome:
        outcome_found = (
            ("outcome" in parsed and isinstance(parsed["outcome"], str))
            or (isinstance(parsed.get("good"), dict) and "outcome" in parsed["good"])
        )
        if not outcome_found:
            raise FixtureSchemaError(
                f"expected.yaml for {catalog_id} does not contain an outcome specification"
            )

    return parsed


def validate_fixture_directory_structure(
    fixture_dir: Path,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Validate that fixture_dir contains valid good.json, bad.json, and expected.yaml.

    Args:
        fixture_dir: Path to directory for a specific catalog item (e.g., catalog/fixtures/DSP001).

    Returns:
        Tuple of (good_dict, bad_dict, expected_dict).

    Raises:
        FixtureNotFoundError: If fixture_dir or any required file is missing.
        FixtureSchemaError: If any file contains malformed JSON/YAML or fails schema rules.
    """
    if not fixture_dir.is_dir():
        raise FixtureNotFoundError(f"Fixture directory not found: {fixture_dir}")

    good_path = fixture_dir / "good.json"
    bad_path = fixture_dir / "bad.json"
    expected_path = fixture_dir / "expected.yaml"

    for file_path, name in [
        (good_path, "good.json"),
        (bad_path, "bad.json"),
        (expected_path, "expected.yaml"),
    ]:
        if not file_path.is_file():
            raise FixtureNotFoundError(f"Required fixture file missing: {name} in {fixture_dir}")

    # Load and validate good.json
    try:
        with open(good_path, encoding="utf-8") as f:
            good_data: Any = json.load(f)
    except json.JSONDecodeError as exc:
        raise FixtureSchemaError(f"Malformed JSON in {good_path}: {exc}") from exc

    if not isinstance(good_data, dict):
        raise FixtureSchemaError(
            f"good.json in {fixture_dir} must be a JSON object, got {type(good_data)}"
        )

    # Load and validate bad.json
    try:
        with open(bad_path, encoding="utf-8") as f:
            bad_data: Any = json.load(f)
    except json.JSONDecodeError as exc:
        raise FixtureSchemaError(f"Malformed JSON in {bad_path}: {exc}") from exc

    if not isinstance(bad_data, dict):
        raise FixtureSchemaError(
            f"bad.json in {fixture_dir} must be a JSON object, got {type(bad_data)}"
        )

    # Load and validate expected.yaml
    try:
        with open(expected_path, encoding="utf-8") as f:
            raw_yaml = f.read()
    except Exception as exc:
        raise FixtureSchemaError(f"Failed to read {expected_path}: {exc}") from exc

    expected_data = validate_expected_yaml_content(raw_yaml)

    if expected_data["id"] != fixture_dir.name:
        raise FixtureSchemaError(
            f"Catalog ID mismatch in {expected_path}: "
            f"expected '{fixture_dir.name}', got '{expected_data['id']}'"
        )

    return good_data, bad_data, expected_data
