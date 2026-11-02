"""Verification test harness and fixture runner module."""

from tests.harness.fixture_runner import (
    CatalogFixtureRunner,
    FixturePassResult,
    FixtureResult,
)
from tests.harness.schema_validator import (
    FixtureError,
    FixtureNotFoundError,
    FixtureSchemaError,
    validate_catalog_schema_file,
    validate_expected_yaml_content,
    validate_fixture_directory_structure,
)

__all__ = [
    "CatalogFixtureRunner",
    "FixtureError",
    "FixtureNotFoundError",
    "FixturePassResult",
    "FixtureResult",
    "FixtureSchemaError",
    "validate_catalog_schema_file",
    "validate_expected_yaml_content",
    "validate_fixture_directory_structure",
]
