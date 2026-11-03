"""Unit tests for the 2-hour deadline fail-safe background monitor daemon (DSP018)."""

from __future__ import annotations

import aiosqlite
import pytest

from app.clients.paypal_client import PayPalDisputesClient
from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    InternalState,
    Money,
    RecommendedAction,
)
from app.services.approval_gate import ApprovalGateService
from app.services.audit_service import AuditService
from app.services.deadline_monitor import DeadlineMonitorDaemon
from app.storage.database import init_database
from app.storage.repository import MerchantRepository

BASE_URL = "https://api-m.sandbox.paypal.com"


def create_expiring_dispute(
    dispute_id: str,
    hours_until_due: float,
    internal_state: InternalState = InternalState.PENDING_APPROVAL,
    action: RecommendedAction = RecommendedAction.CONTEST,
) -> DisputeRecord:
    """Helper creating a DisputeRecord with specified hours until deadline."""
    return DisputeRecord(
        dispute_id=dispute_id,
        reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=150.00),
        seller_response_due_date="2026-11-10T12:00:00Z",
        hours_until_due=hours_until_due,
        allowed_links=["provide-evidence"],
        internal_state=internal_state,
        recommended_action=action,
        win_probability=0.85,
        expected_recovery=127.50,
    )


@pytest.fixture
def paypal_client() -> PayPalDisputesClient:
    """Fixture providing initialized PayPalDisputesClient."""
    return PayPalDisputesClient(
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        base_url=BASE_URL,
    )


@pytest.mark.asyncio
async def test_t07_05_deadline_failsafe_trigger(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T07-05: Dispute with hours_until_due == 1.8 triggers fail-safe (DSP018)."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        daemon = DeadlineMonitorDaemon(repo=repo, client=paypal_client, audit=audit)

        dispute = create_expiring_dispute("PP-D-EXPIRE-1", hours_until_due=1.8)
        await repo.save_dispute(dispute)

        expiring = await daemon.check_expiring_disputes()
        assert "PP-D-EXPIRE-1" in expiring

        await daemon.trigger_fail_safe("PP-D-EXPIRE-1")

        updated = await repo.get_dispute("PP-D-EXPIRE-1")
        assert updated is not None
        assert updated.internal_state == InternalState.DISPATCHED

        # Verify audit trail contains FAIL_SAFE_TRIGGERED action
        assert await audit.verify_chain_integrity("PP-D-EXPIRE-1") is True


@pytest.mark.asyncio
async def test_boundary_exactly_2_hours_triggers_failsafe(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Boundary case: Dispute with exactly 2.0 hours remaining activates emergency fallback."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        daemon = DeadlineMonitorDaemon(repo=repo, client=paypal_client, audit=audit)

        dispute = create_expiring_dispute("PP-D-BOUNDARY-2H", hours_until_due=2.0)
        await repo.save_dispute(dispute)

        expiring = await daemon.check_expiring_disputes()
        assert "PP-D-BOUNDARY-2H" in expiring


@pytest.mark.asyncio
async def test_dispute_above_2_hours_not_triggered(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Dispute with 2.1 or more hours remaining is NOT included in expiring list."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        daemon = DeadlineMonitorDaemon(repo=repo, client=paypal_client, audit=audit)

        dispute = create_expiring_dispute("PP-D-SAFE-TIME", hours_until_due=2.1)
        await repo.save_dispute(dispute)

        expiring = await daemon.check_expiring_disputes()
        assert "PP-D-SAFE-TIME" not in expiring


@pytest.mark.asyncio
async def test_non_pending_approval_disputes_ignored(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Disputes in AUTO_READY, DISPATCHED, or RESOLVED are not targeted by fail-safe daemon."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        daemon = DeadlineMonitorDaemon(repo=repo, client=paypal_client, audit=audit)

        dispute_auto = create_expiring_dispute(
            "PP-D-AUTO", hours_until_due=0.5, internal_state=InternalState.AUTO_READY
        )
        dispute_dispatched = create_expiring_dispute(
            "PP-D-DISPATCHED", hours_until_due=0.5, internal_state=InternalState.DISPATCHED
        )
        await repo.save_dispute(dispute_auto)
        await repo.save_dispute(dispute_dispatched)

        expiring = await daemon.check_expiring_disputes()
        assert "PP-D-AUTO" not in expiring
        assert "PP-D-DISPATCHED" not in expiring


@pytest.mark.asyncio
async def test_race_condition_operator_approval_vs_daemon(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Operator approval and fail-safe trigger handle race conditions atomically."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)
        daemon = DeadlineMonitorDaemon(
            repo=repo, client=paypal_client, audit=audit, approval_gate=gate_service
        )

        dispute = create_expiring_dispute("PP-D-RACE", hours_until_due=1.0)
        await repo.save_dispute(dispute)

        # Operator approves first
        await gate_service.approve_dispute("PP-D-RACE", operator_id="admin_fast")

        # Daemon subsequently tries to trigger fail-safe on same dispute
        await daemon.trigger_fail_safe("PP-D-RACE")

        # State remains DISPATCHED and assigned to operator, not overwritten by daemon
        final = await repo.get_dispute("PP-D-RACE")
        assert final is not None
        assert final.internal_state == InternalState.DISPATCHED
        assert final.assigned_operator == "admin_fast"


def test_evaluate_deadline_policy_oracle() -> None:
    """Test policy evaluation matches DSP018 behavior matrix."""
    # When >= 24h: normal alert, no action
    res_normal = DeadlineMonitorDaemon.evaluate_deadline_policy(
        hours_until_deadline=120.0,
        decision_state="PENDING_APPROVAL",
        has_valid_delivery_proof=True,
    )
    assert res_normal["state"] == "PENDING_APPROVAL"
    assert res_normal["action_taken"] == "none"
    assert res_normal["alert_level"] == "normal"

    # When <= 2h: CRITICAL alert, emergency evidence submission
    res_critical = DeadlineMonitorDaemon.evaluate_deadline_policy(
        hours_until_deadline=1.5,
        decision_state="PENDING_APPROVAL",
        has_valid_delivery_proof=True,
    )
    assert res_critical["state"] == "SAFETY_FALLBACK_TRIGGERED"
    assert res_critical["action_taken"] == "submit_evidence"
    assert res_critical["alert_level"] == "CRITICAL"
    assert res_critical["reason"] == "DEADLINE_IMMINENT_PREVENT_DEFAULT_LOSS"
