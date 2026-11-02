"""Unit tests for tamper-evident SHA-256 audit trail service (DSP022)."""

from __future__ import annotations

import aiosqlite
import pytest

from app.services.audit_service import AuditService
from app.storage.database import init_database


@pytest.fixture
async def db_conn():
    """In-memory SQLite connection for testing."""
    conn = await aiosqlite.connect(":memory:")
    await init_database(conn)
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_t03_03_tamper_evident_audit_trail_chain(db_conn: aiosqlite.Connection) -> None:
    """T03-03: Tamper-evident audit trail chain (DSP022).

    Append 3 sequential audit entries.
    Entry 2 prev_hash equals Entry 1 entry_hash; Entry 3 prev_hash equals Entry 2 entry_hash.
    """
    audit = AuditService(db_conn)
    dispute_id = "PP-D-1022"

    entry1 = await audit.log_action(
        dispute_id=dispute_id,
        action="RECEIVED",
        actor="SYSTEM_AI",
        details={"status": "INGESTED"},
    )
    assert entry1.prev_hash == "0" * 64
    assert len(entry1.entry_hash) == 64

    entry2 = await audit.log_action(
        dispute_id=dispute_id,
        action="EVALUATED",
        actor="SYSTEM_AI",
        details={"recommendation": "CONTEST"},
    )
    assert entry2.prev_hash == entry1.entry_hash
    assert len(entry2.entry_hash) == 64

    entry3 = await audit.log_action(
        dispute_id=dispute_id,
        action="APPROVED",
        actor="OPERATOR_HUMAN",
        details={"assigned_operator": "operator_sarah"},
    )
    assert entry3.prev_hash == entry2.entry_hash
    assert len(entry3.entry_hash) == 64

    # Verify overall chain integrity
    is_valid = await audit.verify_chain_integrity(dispute_id)
    assert is_valid is True
    # Verify alias
    assert await audit.verify_audit_integrity(dispute_id) is True


@pytest.mark.asyncio
async def test_t03_04_audit_trail_tampering_detection(db_conn: aiosqlite.Connection) -> None:
    """T03-04: Audit trail tampering detection (DSP022).

    Mutate action field in Entry 1 directly in database.
    verify_audit_integrity() returns False.
    """
    audit = AuditService(db_conn)
    dispute_id = "PP-D-1022"

    entry1 = await audit.log_action(
        dispute_id=dispute_id,
        action="RECEIVED",
        actor="SYSTEM_AI",
        details={"status": "INGESTED"},
    )
    await audit.log_action(
        dispute_id=dispute_id,
        action="APPROVED",
        actor="OPERATOR_HUMAN",
        details={"status": "APPROVED"},
    )

    # Disable trigger temporarily to simulate malicious database tampering
    await db_conn.execute("DROP TRIGGER IF EXISTS prevent_audit_log_update;")
    await db_conn.execute(
        "UPDATE audit_log SET action = 'MALICIOUS_OVERRIDE' WHERE entry_id = ?",
        (entry1.entry_id,),
    )
    await db_conn.commit()

    # Re-verify audit integrity
    is_valid = await audit.verify_audit_integrity(dispute_id)
    assert is_valid is False

    # Also test corrupt JSON in details field
    await db_conn.execute(
        "UPDATE audit_log SET details = 'NOT_JSON' WHERE entry_id = ?",
        (entry1.entry_id,),
    )
    await db_conn.commit()
    assert await audit.verify_chain_integrity(dispute_id) is False


@pytest.mark.asyncio
async def test_boundary_empty_audit_log_returns_true(db_conn: aiosqlite.Connection) -> None:
    """Boundary case: Empty audit log returns verify_audit_integrity() == True."""
    audit = AuditService(db_conn)
    assert await audit.verify_chain_integrity("NON_EXISTENT_DISPUTE") is True


@pytest.mark.asyncio
async def test_audit_log_scrubs_pci_data_in_details(db_conn: aiosqlite.Connection) -> None:
    """Ensure PAN numbers and CVVs inside action details are scrubbed before persistence."""
    audit = AuditService(db_conn)
    dispute_id = "PP-D-9999"

    entry = await audit.log_action(
        dispute_id=dispute_id,
        action="CUSTOMER_MESSAGE",
        actor="OPERATOR_HUMAN",
        details={
            "note": "Card was 4532015698741235 CVV 999",
            "nested": {"pan": "4111 2222 3333 4444"},
        },
    )

    assert "4532015698741235" not in entry.details["note"]
    assert "999" not in entry.details["note"]
    assert "4111 2222 3333 4444" not in entry.details["nested"]["pan"]
    assert "4532-XXXX-XXXX-1235" in entry.details["note"]
    assert "4111-XXXX-XXXX-4444" in entry.details["nested"]["pan"]


@pytest.mark.asyncio
async def test_audit_log_immutability_trigger(db_conn: aiosqlite.Connection) -> None:
    """Ensure database triggers abort UPDATE and DELETE operations on audit_log."""
    audit = AuditService(db_conn)
    dispute_id = "PP-D-IMMUTABLE"

    entry = await audit.log_action(
        dispute_id=dispute_id,
        action="INGESTED",
        actor="SYSTEM_AI",
        details={},
    )

    with pytest.raises(Exception, match="AUDIT_LOG_IMMUTABLE"):
        await db_conn.execute(
            "UPDATE audit_log SET action = 'MUTATED' WHERE entry_id = ?",
            (entry.entry_id,),
        )

    with pytest.raises(Exception, match="AUDIT_LOG_IMMUTABLE"):
        await db_conn.execute(
            "DELETE FROM audit_log WHERE entry_id = ?",
            (entry.entry_id,),
        )
