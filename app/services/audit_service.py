"""Tamper-evident audit trail service using SHA-256 hash chaining (DSP022)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import aiosqlite

from app.domain.models import AuditTrailEntry
from app.services.sanitizer import PCISanitizer

INITIAL_PREV_HASH: str = "0" * 64


def compute_entry_hash(
    entry_id: str,
    timestamp: str,
    dispute_id: str,
    action: str,
    actor: str,
    details: dict[str, Any],
    prev_hash: str,
) -> str:
    """Compute deterministic SHA-256 hash over canonical payload and previous entry hash."""
    payload_dict: dict[str, Any] = {
        "action": action,
        "actor": actor,
        "details": details,
        "dispute_id": dispute_id,
        "entry_id": entry_id,
        "timestamp": timestamp,
    }
    canonical_json = json.dumps(payload_dict, sort_keys=True, separators=(",", ":"))
    hash_payload = canonical_json.encode("utf-8") + prev_hash.encode("utf-8")
    return hashlib.sha256(hash_payload).hexdigest()


class AuditService:
    """Service for logging and verifying tamper-evident cryptographic audit records."""

    def __init__(self, db_conn: aiosqlite.Connection) -> None:
        self.db = db_conn

    async def get_latest_hash(self, dispute_id: str) -> str:
        """Retrieve entry_hash of the most recent audit entry for dispute, or initial zeros."""
        async with self.db.execute(
            "SELECT entry_hash FROM audit_log WHERE dispute_id = ? ORDER BY rowid DESC LIMIT 1",
            (dispute_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None and row[0]:
                return str(row[0])
            return INITIAL_PREV_HASH

    async def log_action(
        self,
        dispute_id: str,
        action: str,
        actor: str,
        details: dict[str, Any],
        previous_state: str | None = None,
        new_state: str | None = None,
    ) -> AuditTrailEntry:
        """Record an immutable, cryptographically chained audit log entry.

        Args:
            dispute_id: Identifier of the associated dispute.
            action: Action or state transition performed.
            actor: Identity of actor performing the action.
            details: Contextual payload metadata (scrubbed of PCI DSS PAN/CVV).
            previous_state: Optional previous state for dispute lifecycle tracking.
            new_state: Optional new state for dispute lifecycle tracking.

        Returns:
            Persisted AuditTrailEntry instance.
        """
        # Strict zero-PAN rule: Sanitize any credit card numbers or CVVs in details payload
        scrubbed_details = PCISanitizer.sanitize_data(details)

        prev_hash = await self.get_latest_hash(dispute_id)
        entry_id = str(uuid4())
        timestamp = datetime.now(UTC).isoformat()

        entry_hash = compute_entry_hash(
            entry_id=entry_id,
            timestamp=timestamp,
            dispute_id=dispute_id,
            action=action,
            actor=actor,
            details=scrubbed_details,
            prev_hash=prev_hash,
        )

        resolved_prev_state = previous_state or scrubbed_details.get("previous_state")
        resolved_new_state = new_state or scrubbed_details.get("new_state", action)

        entry = AuditTrailEntry(
            entry_id=entry_id,
            timestamp=timestamp,
            dispute_id=dispute_id,
            action=action,
            actor=actor,
            details=scrubbed_details,
            prev_hash=prev_hash,
            entry_hash=entry_hash,
            previous_state=str(resolved_prev_state) if resolved_prev_state is not None else None,
            new_state=str(resolved_new_state) if resolved_new_state is not None else None,
        )

        details_json = json.dumps(scrubbed_details, sort_keys=True)
        await self.db.execute(
            """
            INSERT INTO audit_log (
                entry_id, timestamp, dispute_id, action, actor, details, prev_hash, entry_hash,
                previous_state, new_state, actor_id, payload_summary
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.entry_id,
                entry.timestamp,
                entry.dispute_id,
                entry.action,
                entry.actor,
                details_json,
                entry.prev_hash,
                entry.entry_hash,
                entry.previous_state,
                entry.new_state,
                entry.actor,
                details_json,
            ),
        )
        await self.db.commit()
        return entry

    async def verify_chain_integrity(self, dispute_id: str) -> bool:
        """Verify SHA-256 cryptographic chaining integrity for a dispute's audit trail.

        Returns:
            True if all records in the chain are valid and uncorrupted, False otherwise.
        """
        async with self.db.execute(
            """
            SELECT entry_id, timestamp, dispute_id, action, actor, details, prev_hash, entry_hash
            FROM audit_log
            WHERE dispute_id = ?
            ORDER BY rowid ASC
            """,
            (dispute_id,),
        ) as cursor:
            rows = await cursor.fetchall()

        if not rows:
            return True

        expected_prev = INITIAL_PREV_HASH
        for row in rows:
            entry_id = str(row[0])
            timestamp = str(row[1])
            row_dispute_id = str(row[2])
            action = str(row[3])
            actor = str(row[4])
            raw_details = str(row[5])
            prev_hash = str(row[6])
            entry_hash = str(row[7])

            if prev_hash != expected_prev:
                return False

            try:
                details_dict: dict[str, Any] = json.loads(raw_details)
            except Exception:
                return False

            computed = compute_entry_hash(
                entry_id=entry_id,
                timestamp=timestamp,
                dispute_id=row_dispute_id,
                action=action,
                actor=actor,
                details=details_dict,
                prev_hash=prev_hash,
            )

            if computed != entry_hash:
                return False

            expected_prev = entry_hash

        return True

    # Alias per S03-tests.md naming convention
    verify_audit_integrity = verify_chain_integrity
