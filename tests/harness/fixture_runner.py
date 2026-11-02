"""Automated fixture runner for DisputeSentry AI behavior catalog items."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from tests.harness.schema_validator import (
    FixtureNotFoundError,
    FixtureSchemaError,
    validate_fixture_directory_structure,
)


class FixtureResult(BaseModel):
    """Result of an oracle check execution for a catalog item fixture."""

    catalog_id: str
    status: str  # "PASSED", "FAILED", "SKIPPED"
    details: str


class FixturePassResult(FixtureResult):
    """Convenience subclass representing a successful oracle verification."""

    status: str = Field(default="PASSED")


HandlerCallable = Callable[
    [dict[str, Any], dict[str, Any], dict[str, Any]],
    FixtureResult,
]


class CatalogFixtureRunner:
    """Discovers, loads, and executes verification tests against catalog fixtures."""

    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir
        self._handlers: dict[str, HandlerCallable] = {}

    def register_handler(self, catalog_id: str, handler: HandlerCallable) -> None:
        """Register a dynamic domain execution handler for a specific catalog ID.

        Enables future stages (S02 - S09) to plug in domain behavior testing
        without modifying this verification harness.
        """
        self._handlers[catalog_id] = handler

    def discover_fixtures(self) -> list[str]:
        """Enumerate and sort all catalog fixture subdirectories matching DSP###."""
        if not self.fixtures_dir.is_dir():
            raise FixtureNotFoundError(f"Fixtures directory not found: {self.fixtures_dir}")

        discovered: list[str] = []
        for entry in sorted(self.fixtures_dir.iterdir()):
            if entry.is_dir() and not entry.name.startswith("."):
                if entry.name.startswith("DSP") and entry.name[3:].isdigit():
                    discovered.append(entry.name)
        return discovered

    def load_fixture(
        self, catalog_id: str
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Load good.json, bad.json, and expected.yaml for the given catalog_id.

        Args:
            catalog_id: Catalog item ID (e.g., 'DSP001').

        Returns:
            Tuple of (good_payload, bad_payload, expected_dict).

        Raises:
            FixtureNotFoundError: If directory or any required file is missing.
            FixtureSchemaError: If any file fails schema or parsing validation.
        """
        fixture_path = self.fixtures_dir / catalog_id
        if not fixture_path.is_dir():
            raise FixtureNotFoundError(
                f"Fixture directory not found for {catalog_id}: {fixture_path}"
            )
        return validate_fixture_directory_structure(fixture_path)

    def execute_oracle_check(self, catalog_id: str) -> FixtureResult:
        """Execute oracle verification for a catalog fixture.

        In S01, the oracle checks verify fixture integrity and schema compliance.
        If a domain handler has been registered for catalog_id, it is executed.
        """
        try:
            good, bad, expected = self.load_fixture(catalog_id)
        except (FixtureNotFoundError, FixtureSchemaError) as exc:
            return FixtureResult(
                catalog_id=catalog_id,
                status="FAILED",
                details=f"Fixture load error: {exc}",
            )

        if catalog_id in self._handlers:
            try:
                return self._handlers[catalog_id](good, bad, expected)
            except Exception as exc:
                return FixtureResult(
                    catalog_id=catalog_id,
                    status="FAILED",
                    details=f"Handler execution error: {exc}",
                )

        return FixturePassResult(
            catalog_id=catalog_id,
            status="PASSED",
            details="Fixture integrity and schema verified",
        )
