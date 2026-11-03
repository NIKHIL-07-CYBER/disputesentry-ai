"""Deadline monitor daemon and 2-hour fail-safe automated fallback (DSP018)."""

from __future__ import annotations

import logging
from typing import Any

from app.clients.paypal_client import PayPalDisputesClient
from app.domain.models import InternalState, RecommendedAction
from app.services.approval_gate import ApprovalGateService, DisputeNotFoundError
from app.services.audit_service import AuditService
from app.storage.repository import MerchantRepository

logger = logging.getLogger(__name__)


class DeadlineMonitorDaemon:
    """Background monitor scanning pending disputes and executing safe fallbacks near deadlines.

    Safeguards disputes in PENDING_APPROVAL approaching 2-hour window (DSP018).
    """

    def __init__(
        self,
        repo: MerchantRepository,
        client: PayPalDisputesClient,
        audit: AuditService,
        approval_gate: ApprovalGateService | None = None,
        fail_safe_threshold_hours: float = 2.0,
        alert_threshold_hours: float = 24.0,
    ) -> None:
        self.repo = repo
        self.client = client
        self.audit = audit
        self.approval_gate = approval_gate
        self.fail_safe_threshold_hours = fail_safe_threshold_hours
        self.alert_threshold_hours = alert_threshold_hours

    @classmethod
    def evaluate_deadline_policy(
        cls,
        hours_until_deadline: float,
        decision_state: str = "PENDING_APPROVAL",
        has_valid_delivery_proof: bool = True,
        recommended_action: str = "CONTEST",
    ) -> dict[str, Any]:
        """Classify dispute urgency tier and evaluate fail-safe action against DSP018 policy.

        Args:
            hours_until_deadline: Hours remaining until response deadline.
            decision_state: Current internal decision state of dispute.
            has_valid_delivery_proof: Whether merchant store has valid delivery records.
            recommended_action: Engine recommended action (CONTEST or CONCEDE).

        Returns:
            Dictionary with evaluated state, action_taken, alert_level, and reason.
        """
        if hours_until_deadline <= 2.0 and decision_state == "PENDING_APPROVAL":
            action = (
                "submit_evidence"
                if has_valid_delivery_proof or recommended_action == "CONTEST"
                else "concede"
            )
            return {
                "state": "SAFETY_FALLBACK_TRIGGERED",
                "action_taken": action,
                "alert_level": "CRITICAL",
                "reason": "DEADLINE_IMMINENT_PREVENT_DEFAULT_LOSS",
            }
        elif hours_until_deadline <= 24.0:
            return {
                "state": decision_state,
                "action_taken": "none",
                "alert_level": "HIGH",
                "reason": "DEADLINE_APPROACHING",
            }
        else:
            return {
                "state": decision_state,
                "action_taken": "none",
                "alert_level": "normal",
            }

    async def check_expiring_disputes(self) -> list[str]:
        """Scan active disputes in PENDING_APPROVAL approaching the deadline (<= 2 hours).

        Returns:
            List of dispute_ids requiring automated fail-safe execution.
        """
        if self.repo.db is None:
            return []

        async with self.repo.db.execute(
            """
            SELECT dispute_id, hours_until_due
            FROM disputes
            WHERE internal_state = ?
            """,
            (InternalState.PENDING_APPROVAL.value,),
        ) as cursor:
            rows = await cursor.fetchall()

        expiring: list[str] = []
        for row in rows:
            dispute_id = str(row[0])
            hours = float(row[1])
            if hours <= self.fail_safe_threshold_hours:
                expiring.append(dispute_id)

        return expiring

    async def trigger_fail_safe(self, dispute_id: str) -> None:
        """Execute automated fail-safe representation on dispute to prevent default forfeiture.

        Args:
            dispute_id: Identifier of the expiring dispute.

        Raises:
            DisputeNotFoundError: Dispute does not exist.
        """
        dispute = await self.repo.get_dispute(dispute_id)
        if dispute is None:
            raise DisputeNotFoundError(f"Dispute not found: {dispute_id}")

        if dispute.internal_state != InternalState.PENDING_APPROVAL:
            logger.info(
                "Dispute %s is in state %s; skipping fail-safe",
                dispute_id,
                dispute.internal_state.value,
            )
            return

        # Atomically update status in SQLite to DISPATCHED
        if self.repo.db is not None:
            async with self.repo.db.execute(
                """
                UPDATE disputes
                SET internal_state = ?
                WHERE dispute_id = ? AND internal_state = ?
                """,
                (
                    InternalState.DISPATCHED.value,
                    dispute_id,
                    InternalState.PENDING_APPROVAL.value,
                ),
            ) as cursor:
                if cursor.rowcount == 0:
                    logger.info(
                        "Dispute %s state changed concurrently; aborting fail-safe trigger",
                        dispute_id,
                    )
                    return
            await self.repo.db.commit()

        dispute.internal_state = InternalState.DISPATCHED

        if self.audit.db is not None:
            action_taken = (
                "submit_evidence"
                if dispute.recommended_action != RecommendedAction.CONCEDE
                else "concede"
            )
            await self.audit.log_action(
                dispute_id=dispute_id,
                action="FAIL_SAFE_TRIGGERED",
                actor="system:deadline_monitor",
                details={
                    "reason": "DEADLINE_IMMINENT_PREVENT_DEFAULT_LOSS",
                    "hours_until_due": dispute.hours_until_due,
                    "alert_level": "CRITICAL",
                    "action_taken": action_taken,
                },
                previous_state=InternalState.PENDING_APPROVAL.value,
                new_state=InternalState.DISPATCHED.value,
            )

        # Attempt safe dispatch
        if dispute.recommended_action == RecommendedAction.CONCEDE:
            try:
                if self.approval_gate is not None:
                    await self.approval_gate.accept_claim(
                        dispute_id=dispute_id,
                        note="Automatic emergency concession before deadline expiration.",
                        current_status=dispute.status.value,
                    )
                elif hasattr(self.client, "accept_claim"):
                    await self.client.accept_claim(
                        dispute_id,
                        note="Automatic emergency concession before deadline expiration.",
                        status=dispute.status.value,
                    )
            except Exception as exc:
                logger.error("Fail-safe concession failed for %s: %s", dispute_id, exc)
        else:
            try:
                evidence_pkg = await self.repo.assemble_evidence_package(dispute_id)
                if (
                    evidence_pkg.record_found
                    and evidence_pkg.tracking_number
                    and evidence_pkg.carrier
                ):
                    payload = {
                        "evidence_type": "PROOF_OF_FULFILLMENT",
                        "carrier_name": evidence_pkg.carrier,
                        "tracking_number": evidence_pkg.tracking_number,
                        "comments": (
                            "Automated defensive evidence submission by DisputeSentry "
                            "deadline fail-safe."
                        ),
                    }
                    await self.client.provide_evidence(dispute_id, payload)
            except Exception as exc:
                logger.error("Fail-safe evidence upload failed for %s: %s", dispute_id, exc)

        if self.repo.db is not None:
            await self.repo.save_dispute(dispute)
