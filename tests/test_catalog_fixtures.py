"""Behavior catalog fixture discovery, schema validation, and test harness execution."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import aiosqlite
import pytest
import respx

from app.clients.paypal_client import (
    EvidenceValidationError,
    PayPalDisputesClient,
)
from app.domain.models import MerchantOrderRecord
from app.services.audit_service import AuditService
from app.services.dispute_sync import (
    DisputeSyncCoordinator,
    HATEOASViolationError,
    validate_hateoas_action,
    validate_hateoas_action_or_raise,
)
from app.services.sanitizer import PCISanitizer
from app.storage.database import init_database
from app.storage.repository import MerchantRepository
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


def dsp006_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP006: Matching dispute to merchant fulfillment record."""
    async def _run() -> None:
        async with aiosqlite.connect(":memory:") as db:
            await init_database(db)
            repo = MerchantRepository(db)
            for rec in good.get("mock_store_records", []):
                order = MerchantOrderRecord(
                    order_id=rec["order_id"],
                    transaction_id=rec["transaction_id"],
                    buyer_email=rec.get("customer_email", "buyer@example.com"),
                    shipping_address={"country_code": "US", "postal_code": "78701"},
                    carrier=rec.get("carrier", "USPS"),
                    tracking_number=rec.get("tracking_number", "9400100000000000000001"),
                    delivery_status=rec.get("status", "DELIVERED"),
                    shipped_date="2026-10-20T10:00:00Z",
                    delivery_date=rec.get("delivery_date"),
                )
                await repo.save_order(order)

            # Test good transaction match
            pkg_good = await repo.assemble_evidence_package(good["transaction_id"])
            assert pkg_good.record_found is expected["good"]["record_found"]
            assert pkg_good.order is not None
            assert pkg_good.order.order_id == expected["good"]["order_id"]
            assert pkg_good.carrier == expected["good"]["carrier"]
            assert pkg_good.tracking_number == expected["good"]["tracking_number"]

            # Test bad transaction match (missing record)
            pkg_bad = await repo.assemble_evidence_package(bad["transaction_id"])
            assert pkg_bad.record_found is expected["bad"]["record_found"]
            assert pkg_bad.status == expected["bad"]["outcome"]

    asyncio.run(_run())
    return FixturePassResult(
        catalog_id="DSP006",
        status="PASSED",
        details="Merchant order evidence matching verified",
    )


def dsp019_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP019: Redact PAN and card data from dispute records."""
    good_text = good["buyer_note"]
    assert not PCISanitizer.contains_pan(good_text)
    sanitized_good = PCISanitizer.sanitize(good_text, full_redaction=True)
    assert sanitized_good == expected["good"]["output_text"]

    bad_text = bad["buyer_note"]
    assert PCISanitizer.contains_pan(bad_text)
    sanitized_bad = PCISanitizer.sanitize(bad_text, full_redaction=True)
    assert sanitized_bad == expected["bad"]["output_text"]

    return FixturePassResult(
        catalog_id="DSP019",
        status="PASSED",
        details="PCI DSS PAN and CVV scrubbing verified",
    )


def dsp022_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP022: Append-only audit log with SHA-256 state hashes."""
    async def _run() -> None:
        async with aiosqlite.connect(":memory:") as db:
            await init_database(db)
            audit = AuditService(db)

            # Good: Append audit entry
            entry = await audit.log_action(
                dispute_id=good["dispute_id"],
                action=good.get("new_state", "STATE_TRANSITION"),
                actor=good.get("actor_id", "operator"),
                details=good.get("payload_metadata", {}),
            )
            assert entry.entry_hash != ""
            assert len(entry.entry_hash) == 64
            assert await audit.verify_chain_integrity(good["dispute_id"]) is True

            # Bad: Attempt to mutate audit entry directly via SQL
            mutated = False
            try:
                await db.execute(bad["sql_command"])
                await db.commit()
            except Exception as exc:
                if "AUDIT_LOG_IMMUTABLE" in str(exc):
                    mutated = True

            assert mutated is expected["bad"]["prohibited"]

    asyncio.run(_run())
    return FixturePassResult(
        catalog_id="DSP022",
        status="PASSED",
        details="Append-only immutable audit trail and SHA-256 state hashing verified",
    )


def dsp005_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP005: Validate allowed dispute action links."""
    good_action = str(expected["good"]["action"])
    assert (
        validate_hateoas_action(good.get("links", []), good_action)
        is expected["good"]["allowed"]
    )
    validate_hateoas_action_or_raise(good.get("links", []), good_action)

    bad_action = str(expected["bad"]["action"])
    assert (
        validate_hateoas_action(bad.get("links", []), bad_action)
        is expected["bad"]["allowed"]
    )
    with pytest.raises(HATEOASViolationError) as exc_info:
        validate_hateoas_action_or_raise(bad.get("links", []), bad_action)
    assert exc_info.value.error_code == expected["bad"]["error_code"]

    return FixturePassResult(
        catalog_id="DSP005",
        status="PASSED",
        details="HATEOAS dispute action link validation verified",
    )


def dsp010_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP010: Calculate dispute deadline urgency tier."""
    coordinator = DisputeSyncCoordinator(
        client=PayPalDisputesClient("id", "secret", "https://api-m.sandbox.paypal.com"),
        repo=MerchantRepository(None),  # type: ignore[arg-type]
        audit=AuditService(None),  # type: ignore[arg-type]
    )

    hours_good, tier_good = coordinator.compute_deadline_urgency(
        good["seller_response_due_date"], good["current_time"]
    )
    assert hours_good == expected["good"]["hours_remaining"]
    assert tier_good == expected["good"]["urgency_tier"]
    assert (hours_good > 0) is expected["good"]["can_submit"]

    hours_bad, tier_bad = coordinator.compute_deadline_urgency(
        bad["seller_response_due_date"], bad["current_time"]
    )
    assert hours_bad == expected["bad"]["hours_remaining"]
    assert tier_bad == expected["bad"]["urgency_tier"]
    assert (hours_bad > 0) is expected["bad"]["can_submit"]

    return FixturePassResult(
        catalog_id="DSP010",
        status="PASSED",
        details="Response deadline urgency calculation and tiering verified",
    )


def dsp014_handler(
    good: dict[str, Any], bad: dict[str, Any], expected: dict[str, Any]
) -> FixtureResult:
    """Domain oracle handler for DSP014: Provide-evidence API call with tracking details."""
    async def _run() -> None:
        client = PayPalDisputesClient(
            client_id="mock_id",
            client_secret="mock_secret",
            base_url="https://api-m.sandbox.paypal.com",
        )
        api_path = str(expected["good"]["api_path"])
        with respx.mock(assert_all_called=False) as router:
            router.post("https://api-m.sandbox.paypal.com/v1/oauth2/token").respond(
                status_code=200,
                json={"access_token": "token_dsp014", "expires_in": 3600},
            )
            evidence_route = router.post(
                f"https://api-m.sandbox.paypal.com{api_path}"
            ).respond(
                status_code=int(expected["good"]["expected_paypal_status"]),
                json={"status": expected["good"]["new_state"]},
            )

            # Test good submission
            res = await client.provide_evidence(str(good["dispute_id"]), good)
            assert evidence_route.called
            assert res.get("status") == expected["good"]["new_state"]

            # Test bad submission (blocked before dispatch)
            with pytest.raises(EvidenceValidationError) as exc_info:
                await client.provide_evidence(str(bad["dispute_id"]), bad)
            assert exc_info.value.error_code == expected["bad"]["validation_error"]

        await client.aclose()

    asyncio.run(_run())
    return FixturePassResult(
        catalog_id="DSP014",
        status="PASSED",
        details="Provide-evidence API dispatch and compulsory tracking validation verified",
    )


@pytest.fixture
def runner(fixtures_dir: Path) -> CatalogFixtureRunner:
    """Fixture providing an initialized CatalogFixtureRunner instance."""
    instance = CatalogFixtureRunner(fixtures_dir=fixtures_dir)
    instance.register_handler("DSP005", dsp005_handler)
    instance.register_handler("DSP006", dsp006_handler)
    instance.register_handler("DSP010", dsp010_handler)
    instance.register_handler("DSP014", dsp014_handler)
    instance.register_handler("DSP019", dsp019_handler)
    instance.register_handler("DSP022", dsp022_handler)
    return instance


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


def test_dsp006_fulfillment_record_match(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP006: Matching dispute to merchant fulfillment record."""
    result = runner.execute_oracle_check("DSP006")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP006"


def test_dsp019_pci_cardholder_scrubbing(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP019: PCI DSS cardholder and CVV scrubbing."""
    result = runner.execute_oracle_check("DSP019")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP019"


def test_dsp022_cryptographic_audit_trail(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP022: Tamper-evident SHA-256 audit log."""
    result = runner.execute_oracle_check("DSP022")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP022"


def test_dsp005_hateoas_action_validation(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP005: Validate allowed dispute action links."""
    result = runner.execute_oracle_check("DSP005")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP005"


def test_dsp010_deadline_urgency_calculation(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP010: Calculate dispute response deadline and urgency."""
    result = runner.execute_oracle_check("DSP010")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP010"


def test_dsp014_provide_evidence_api_submission(runner: CatalogFixtureRunner) -> None:
    """Explicit catalog oracle test for DSP014: Execute provide-evidence API call with tracking."""
    result = runner.execute_oracle_check("DSP014")
    assert result.status == "PASSED"
    assert result.catalog_id == "DSP014"


