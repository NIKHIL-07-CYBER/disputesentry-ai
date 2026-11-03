"""Integration tests for approval gate and concession executor (DSP013, DSP015)."""

from __future__ import annotations

import aiosqlite
import pytest
import respx
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.api.approvals import get_approval_gate_service
from app.api.approvals import router as approvals_router
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
from app.services.approval_gate import (
    ApprovalGateService,
    DisputeAlreadyClosedError,
    DisputeNotFoundError,
    InvalidStateTransitionError,
)
from app.services.audit_service import AuditService
from app.storage.database import init_database
from app.storage.repository import MerchantRepository

BASE_URL = "https://api-m.sandbox.paypal.com"


def create_dispute_record(
    dispute_id: str = "PP-D-1013",
    amount: float = 45.00,
    action: RecommendedAction = RecommendedAction.CONTEST,
    win_probability: float = 0.88,
    internal_state: InternalState = InternalState.EVALUATING,
    status: DisputeStatus = DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
    hours_until_due: float = 72.0,
) -> DisputeRecord:
    """Helper creating a DisputeRecord for test scenarios."""
    return DisputeRecord(
        dispute_id=dispute_id,
        reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        status=status,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=amount),
        seller_response_due_date="2026-11-10T12:00:00Z",
        hours_until_due=hours_until_due,
        allowed_links=["provide-evidence", "accept-claim"],
        internal_state=internal_state,
        recommended_action=action,
        win_probability=win_probability,
        expected_recovery=amount * win_probability,
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
async def test_t07_01_high_value_dispute_approval_lock(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T07-01: Dispute amount $120.00 (> $100.00) transitions to PENDING_APPROVAL (DSP013)."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-HIGH-VAL",
            amount=120.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.90,
            internal_state=InternalState.EVALUATING,
        )
        await repo.save_dispute(dispute)

        new_state = await gate_service.evaluate_gate(dispute)
        assert new_state == InternalState.PENDING_APPROVAL

        saved = await repo.get_dispute("PP-D-HIGH-VAL")
        assert saved is not None
        assert saved.internal_state == InternalState.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_t07_02_low_value_dispute_auto_readiness(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T07-02: Dispute amount $45.00 (< $100.00), high confidence transitions to AUTO_READY."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-LOW-VAL",
            amount=45.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.88,
            internal_state=InternalState.EVALUATING,
        )
        await repo.save_dispute(dispute)

        new_state = await gate_service.evaluate_gate(dispute)
        assert new_state == InternalState.AUTO_READY

        saved = await repo.get_dispute("PP-D-LOW-VAL")
        assert saved is not None
        assert saved.internal_state == InternalState.AUTO_READY


@pytest.mark.asyncio
async def test_t07_03_concession_action_requires_approval(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T07-03: Dispute amount $30.00 (< $100.00), action CONCEDE requires review (DSP015)."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-CONCEDE",
            amount=30.00,
            action=RecommendedAction.CONCEDE,
            win_probability=0.10,
            internal_state=InternalState.EVALUATING,
        )
        await repo.save_dispute(dispute)

        new_state = await gate_service.evaluate_gate(dispute)
        assert new_state == InternalState.PENDING_APPROVAL

        saved = await repo.get_dispute("PP-D-CONCEDE")
        assert saved is not None
        assert saved.internal_state == InternalState.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_boundary_exactly_100_usd_requires_approval(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Boundary case: Dispute amount exactly $100.00 requires operator approval."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-100-BOUNDARY",
            amount=100.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.85,
            internal_state=InternalState.EVALUATING,
        )
        await repo.save_dispute(dispute)

        new_state = await gate_service.evaluate_gate(dispute)
        assert new_state == InternalState.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_low_confidence_requires_approval(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Dispute with confidence <= 0.65 requires PENDING_APPROVAL even if amount is low (DSP013)."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-LOW-CONF",
            amount=25.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.60,
            internal_state=InternalState.EVALUATING,
        )
        await repo.save_dispute(dispute)

        new_state = await gate_service.evaluate_gate(dispute)
        assert new_state == InternalState.PENDING_APPROVAL


@pytest.mark.asyncio
async def test_operator_approve_transitions_to_dispatched(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Operator approval transitions dispute PENDING_APPROVAL -> APPROVED -> DISPATCHED."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-APPROVE-TEST",
            amount=150.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.85,
            internal_state=InternalState.PENDING_APPROVAL,
        )
        await repo.save_dispute(dispute)

        updated = await gate_service.approve_dispute(
            dispute_id="PP-D-APPROVE-TEST",
            operator_id="operator_alice",
            notes="Representment approved after reviewing order tracking",
        )
        assert updated.internal_state == InternalState.DISPATCHED
        assert updated.assigned_operator == "operator_alice"

        # Verify audit trail contains cryptographic records
        assert await audit.verify_chain_integrity("PP-D-APPROVE-TEST") is True


@pytest.mark.asyncio
async def test_operator_reject_transitions_to_rejected(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Operator rejection transitions dispute PENDING_APPROVAL -> REJECTED."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-REJECT-TEST",
            amount=150.00,
            action=RecommendedAction.CONTEST,
            win_probability=0.85,
            internal_state=InternalState.PENDING_APPROVAL,
        )
        await repo.save_dispute(dispute)

        updated = await gate_service.reject_dispute(
            dispute_id="PP-D-REJECT-TEST",
            operator_id="operator_bob",
            reason="Merchant decided to refund directly",
        )
        assert updated.internal_state == InternalState.REJECTED
        assert updated.assigned_operator == "operator_bob"


@pytest.mark.asyncio
async def test_approve_dispatched_dispute_raises_invalid_state_transition(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Attempting to approve an already DISPATCHED dispute raises InvalidStateTransitionError."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-ALREADY-DISPATCHED",
            amount=150.00,
            internal_state=InternalState.DISPATCHED,
        )
        await repo.save_dispute(dispute)

        with pytest.raises(InvalidStateTransitionError):
            await gate_service.approve_dispute(
                dispute_id="PP-D-ALREADY-DISPATCHED",
                operator_id="operator_alice",
            )


@pytest.mark.asyncio
async def test_approve_nonexistent_dispute_raises_not_found(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Attempting to approve non-existent dispute raises DisputeNotFoundError."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        with pytest.raises(DisputeNotFoundError):
            await gate_service.approve_dispute(
                dispute_id="NON_EXISTENT_ID",
                operator_id="operator_alice",
            )


@pytest.mark.asyncio
async def test_concession_accept_claim_api_call(
    paypal_client: PayPalDisputesClient,
) -> None:
    """DSP015: Approving concession executes accept-claim API with PayPal."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        dispute = create_dispute_record(
            dispute_id="PP-D-1015",
            amount=80.00,
            action=RecommendedAction.CONCEDE,
            internal_state=InternalState.PENDING_APPROVAL,
            status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
        )
        await repo.save_dispute(dispute)

        with respx.mock(assert_all_called=False) as router:
            router.post(f"{BASE_URL}/v1/oauth2/token").respond(
                status_code=200,
                json={"access_token": "mock_token_s07", "expires_in": 3600},
            )
            accept_route = router.post(
                f"{BASE_URL}/v1/customer/disputes/PP-D-1015/accept-claim"
            ).respond(status_code=200, json={})

            res = await gate_service.accept_claim(
                dispute_id="PP-D-1015",
                note="Accepting claim and issuing refund to buyer per merchant return policy.",
                current_status="WAITING_FOR_SELLER_RESPONSE",
            )
            assert accept_route.called
            assert res["status"] == "CLAIM_ACCEPTED"


@pytest.mark.asyncio
async def test_concession_on_resolved_dispute_rejected_locally(
    paypal_client: PayPalDisputesClient,
) -> None:
    """DSP015: Calling accept-claim on an already RESOLVED dispute is rejected locally."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        with pytest.raises(DisputeAlreadyClosedError) as exc_info:
            await gate_service.accept_claim(
                dispute_id="PP-D-1015",
                note="Accepting claim.",
                current_status="RESOLVED",
            )
        assert exc_info.value.error_code == "DISPUTE_ALREADY_CLOSED"


@pytest.mark.asyncio
async def test_t07_04_fastapi_approvals_api_routes(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T07-04: Operator calls POST /api/disputes/{id}/approve and /reject via FastAPI."""
    test_app = FastAPI()
    test_app.include_router(approvals_router)

    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        gate_service = ApprovalGateService(repo=repo, client=paypal_client, audit=audit)

        test_app.dependency_overrides[get_approval_gate_service] = lambda: gate_service

        # Seed dispute in PENDING_APPROVAL
        dispute = create_dispute_record(
            dispute_id="PP-D-API-TEST",
            amount=150.00,
            action=RecommendedAction.CONTEST,
            internal_state=InternalState.PENDING_APPROVAL,
        )
        await repo.save_dispute(dispute)

        async with AsyncClient(
            transport=ASGITransport(app=test_app), base_url="http://test"
        ) as ac:
            # 1. Test POST /api/disputes/{id}/approve
            approve_resp = await ac.post(
                "/api/disputes/PP-D-API-TEST/approve",
                json={"operator_id": "admin", "notes": "Approved for representment"},
            )
            assert approve_resp.status_code == 200
            data = approve_resp.json()
            assert data["internal_state"] == "DISPATCHED"
            assert data["dispute_id"] == "PP-D-API-TEST"

            # 2. Test approving again returns 409 Conflict
            dup_resp = await ac.post(
                "/api/disputes/PP-D-API-TEST/approve",
                json={"operator_id": "admin", "notes": "Duplicate approve"},
            )
            assert dup_resp.status_code == 409

            # 3. Test approving non-existent dispute returns 404
            not_found_resp = await ac.post(
                "/api/disputes/NON-EXISTENT/approve",
                json={"operator_id": "admin"},
            )
            assert not_found_resp.status_code == 404

            # 4. Test POST /api/disputes/{id}/reject on a new dispute
            dispute_reject = create_dispute_record(
                dispute_id="PP-D-API-REJECT",
                amount=150.00,
                internal_state=InternalState.PENDING_APPROVAL,
            )
            await repo.save_dispute(dispute_reject)

            reject_resp = await ac.post(
                "/api/disputes/PP-D-API-REJECT/reject",
                json={"operator_id": "admin", "reason": "Prefer to refund directly"},
            )
            assert reject_resp.status_code == 200
            reject_data = reject_resp.json()
            assert reject_data["internal_state"] == "REJECTED"
