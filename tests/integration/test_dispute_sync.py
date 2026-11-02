"""Integration tests for dispute sync coordinator, HATEOAS validation, and walking skeleton."""

from __future__ import annotations

import aiosqlite
import pytest
import respx

from app.clients.paypal_client import PayPalDisputesClient
from app.domain.models import (
    DisputeRecord,
    InternalState,
    MerchantOrderRecord,
)
from app.services.audit_service import AuditService
from app.services.dispute_sync import (
    DisputeExpiredError,
    DisputeSyncCoordinator,
    HATEOASViolationError,
)
from app.storage.database import init_database
from app.storage.repository import MerchantRepository

BASE_URL = "https://api-m.sandbox.paypal.com"


@pytest.fixture
def paypal_client() -> PayPalDisputesClient:
    """Fixture providing initialized PayPalDisputesClient."""
    return PayPalDisputesClient(
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        base_url=BASE_URL,
    )


@pytest.mark.asyncio
async def test_t04_02_hateoas_link_validation(paypal_client: PayPalDisputesClient) -> None:
    """T04-02: Missing provide_evidence link raises HATEOASViolationError (DSP005)."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        coordinator = DisputeSyncCoordinator(client=paypal_client, repo=repo, audit=audit)

        # Seed matching order
        order = MerchantOrderRecord(
            order_id="ORD-001",
            transaction_id="TX-1005",
            buyer_email="buyer@example.com",
            shipping_address={"country_code": "US", "postal_code": "78701"},
            carrier="USPS",
            tracking_number="9400100000000000000001",
            delivery_status="DELIVERED",
            shipped_date="2026-10-20T10:00:00Z",
            delivery_date="2026-10-25T14:00:00Z",
        )
        await repo.save_order(order)

        # Dispute payload with ONLY accept_claim link, missing provide_evidence
        dispute_resource = {
            "dispute_id": "PP-D-1005",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_life_cycle_stage": "CHARGEBACK",
            "seller_response_due_date": "2026-11-15T12:00:00Z",
            "disputed_transactions": [{"seller_transaction_id": "TX-1005"}],
            "links": [
                {
                    "href": f"{BASE_URL}/v1/customer/disputes/PP-D-1005/accept-claim",
                    "rel": "accept_claim",
                    "method": "POST",
                }
            ],
        }

        with pytest.raises(HATEOASViolationError) as exc_info:
            await coordinator.handle_dispute_event(dispute_resource)

        assert "provide_evidence" in str(exc_info.value)
        assert exc_info.value.error_code == "ACTION_NOT_PERMITTED"

    await paypal_client.aclose()


def test_t04_03_response_due_date_calculation() -> None:
    """T04-03: Remaining hours until response due date classified into urgency tier (DSP010)."""
    coordinator = DisputeSyncCoordinator(
        client=PayPalDisputesClient("id", "secret", BASE_URL),
        repo=MerchantRepository(None),  # type: ignore[arg-type]
        audit=AuditService(None),  # type: ignore[arg-type]
    )

    # T + 36 hours from reference time
    current_time = "2026-11-01T12:00:00Z"
    due_date = "2026-11-03T00:00:00Z"  # exactly 36 hours later

    hours, tier = coordinator.compute_deadline_urgency(due_date, current_time)
    assert hours == 36.0
    assert tier == "MEDIUM"


def test_t04_03_deadline_urgency_boundaries() -> None:
    """T04-03 Boundary cases: Exact thresholds for CRITICAL (24.0h), MEDIUM (72.0h), and LOW."""
    coordinator = DisputeSyncCoordinator(
        client=PayPalDisputesClient("id", "secret", BASE_URL),
        repo=MerchantRepository(None),  # type: ignore[arg-type]
        audit=AuditService(None),  # type: ignore[arg-type]
    )
    current_time = "2026-11-01T12:00:00Z"

    # Exactly 24.0 hours remaining -> CRITICAL
    due_24h = "2026-11-02T12:00:00Z"
    hours_24, tier_24 = coordinator.compute_deadline_urgency(due_24h, current_time)
    assert hours_24 == 24.0
    assert tier_24 == "CRITICAL"

    # Exactly 72.0 hours remaining -> MEDIUM
    due_72h = "2026-11-04T12:00:00Z"
    hours_72, tier_72 = coordinator.compute_deadline_urgency(due_72h, current_time)
    assert hours_72 == 72.0
    assert tier_72 == "MEDIUM"

    # Greater than 72 hours remaining -> LOW
    due_96h = "2026-11-05T12:00:00Z"
    hours_96, tier_96 = coordinator.compute_deadline_urgency(due_96h, current_time)
    assert hours_96 == 96.0
    assert tier_96 == "LOW"


def test_t04_03_expired_deadline_urgency() -> None:
    """T04-03: Past due date yields negative hours and EXPIRED tier."""
    coordinator = DisputeSyncCoordinator(
        client=PayPalDisputesClient("id", "secret", BASE_URL),
        repo=MerchantRepository(None),  # type: ignore[arg-type]
        audit=AuditService(None),  # type: ignore[arg-type]
    )
    current_time = "2026-11-01T12:00:00Z"
    past_due = "2026-10-31T18:00:00Z"  # 18 hours past

    hours, tier = coordinator.compute_deadline_urgency(past_due, current_time)
    assert hours == -18.0
    assert tier == "EXPIRED"


@pytest.mark.asyncio
async def test_t04_03_expired_deadline_raises_dispute_expired_error(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Negative case: Ingesting an expired dispute raises DisputeExpiredError."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)
        coordinator = DisputeSyncCoordinator(client=paypal_client, repo=repo, audit=audit)

        dispute_resource = {
            "dispute_id": "PP-D-EXPIRED",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "seller_response_due_date": "2026-10-01T00:00:00Z",  # In the past
            "disputed_transactions": [{"seller_transaction_id": "TX-ANY"}],
            "links": [{"href": f"{BASE_URL}/...", "rel": "provide_evidence", "method": "POST"}],
        }

        with pytest.raises(DisputeExpiredError) as exc_info:
            await coordinator.handle_dispute_event(dispute_resource)

        assert exc_info.value.error_code == "DEADLINE_EXPIRED"

    await paypal_client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_walking_skeleton_end_to_end(paypal_client: PayPalDisputesClient) -> None:
    """T04-05 Walking skeleton: Webhook -> Order -> HATEOAS Checked -> Dispatched."""
    respx.post(f"{BASE_URL}/v1/oauth2/token").respond(
        status_code=200,
        json={"access_token": "token_skeleton_123", "expires_in": 3600},
    )
    evidence_route = respx.post(
        f"{BASE_URL}/v1/customer/disputes/PP-D-9999/provide-evidence"
    ).respond(
        status_code=200,
        json={"status": "EVIDENCE_SUBMITTED"},
    )

    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)
        audit = AuditService(db)

        # 1. Seed merchant fulfillment store with matching order
        seeded_order = MerchantOrderRecord(
            order_id="ORD-9999",
            transaction_id="TX-9999",
            buyer_email="buyer@example.com",
            shipping_address={"country_code": "US", "postal_code": "78701"},
            carrier="USPS",
            tracking_number="9400100000000000000001",
            delivery_status="DELIVERED",
            shipped_date="2026-10-20T10:00:00Z",
            delivery_date="2026-10-25T14:00:00Z",
        )
        await repo.save_order(seeded_order)

        coordinator = DisputeSyncCoordinator(client=paypal_client, repo=repo, audit=audit)

        # 2. Inbound webhook payload with provide_evidence link and future due date
        webhook_resource = {
            "dispute_id": "PP-D-9999",
            "status": "WAITING_FOR_SELLER_RESPONSE",
            "dispute_life_cycle_stage": "CHARGEBACK",
            "dispute_amount": {"currency": "USD", "value": "75.00"},
            "seller_response_due_date": "2026-11-15T12:00:00Z",
            "disputed_transactions": [{"seller_transaction_id": "TX-9999"}],
            "links": [
                {
                    "href": f"{BASE_URL}/v1/customer/disputes/PP-D-9999/provide-evidence",
                    "rel": "provide_evidence",
                    "method": "POST",
                }
            ],
        }

        # 3. Execute coordinator
        dispute_record: DisputeRecord = await coordinator.handle_dispute_event(webhook_resource)

        # 4. Verify outcomes
        assert dispute_record.dispute_id == "PP-D-9999"
        assert dispute_record.internal_state == InternalState.DISPATCHED
        assert evidence_route.call_count == 1

        # Verify persisted in database
        persisted = await repo.get_dispute("PP-D-9999")
        assert persisted is not None
        assert persisted.internal_state == InternalState.DISPATCHED

        # Verify audit trail recorded
        assert await audit.verify_chain_integrity("PP-D-9999") is True

        # Print the required milestone confirmation string
        msg = (
            "\nEnd-to-end slice verified: Webhook -> Order Lookup -> "
            "HATEOAS Link Checked -> Evidence Dispatched (200 OK)"
        )
        print(msg)

    await paypal_client.aclose()
