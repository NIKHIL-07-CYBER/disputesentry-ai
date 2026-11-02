"""Integration tests for SQLite WAL storage layer, seeded orders, and repositories."""

from __future__ import annotations

import aiosqlite
import pytest

from app.domain.exceptions import OrderNotFoundError
from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    InternalState,
    MerchantOrderRecord,
    Money,
    RecommendedAction,
)
from app.storage.database import init_database
from app.storage.repository import MerchantRepository
from app.storage.seed_data import seed_merchant_orders


@pytest.fixture
async def db_conn():
    """In-memory SQLite connection with tables initialized and orders seeded."""
    conn = await aiosqlite.connect(":memory:")
    await init_database(conn)
    await seed_merchant_orders(conn)
    yield conn
    await conn.close()


@pytest.mark.asyncio
async def test_t03_01_merchant_order_lookup(db_conn: aiosqlite.Connection) -> None:
    """T03-01: Merchant order lookup (DSP006).

    Query TX-1001 against seeded SQLite DB.
    Returns MerchantOrderRecord with order_id ORD-1001 and USPS carrier.
    """
    repo = MerchantRepository(db_conn)
    order = await repo.get_order_by_transaction("TX-1001")
    assert order is not None
    assert isinstance(order, MerchantOrderRecord)
    assert order.order_id == "ORD-1001"
    assert order.carrier == "USPS"
    assert order.tracking_number == "9400100000000000000000"
    assert order.delivery_status == "DELIVERED"


@pytest.mark.asyncio
async def test_positive_seeded_orders_exist(db_conn: aiosqlite.Connection) -> None:
    """Verify seeded orders ORD-1001, ORD-1002, ORD-1003, ORD-1006 exist."""
    repo = MerchantRepository(db_conn)
    for tx_id, order_id in [
        ("TX-1001", "ORD-1001"),
        ("TX-1002", "ORD-1002"),
        ("TX-1003", "ORD-1003"),
        ("TXN-987654321", "ORD-1006"),
    ]:
        order = await repo.get_order_by_transaction(tx_id)
        assert order is not None
        assert order.order_id == order_id


@pytest.mark.asyncio
async def test_negative_unknown_transaction_raises_not_found(db_conn: aiosqlite.Connection) -> None:
    """Negative case: Unknown transaction ID returns None or raises OrderNotFoundError."""
    repo = MerchantRepository(db_conn)
    order = await repo.get_order_by_transaction("TX-NON-EXISTENT")
    assert order is None

    with pytest.raises(OrderNotFoundError):
        await repo.get_order("TX-NON-EXISTENT")


@pytest.mark.asyncio
async def test_dispute_persistence_and_retrieval(db_conn: aiosqlite.Connection) -> None:
    """Verify storing and retrieving a DisputeRecord."""
    repo = MerchantRepository(db_conn)
    dispute = DisputeRecord(
        dispute_id="PP-D-12345",
        create_time="2026-11-01T12:00:00Z",
        reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        status=DisputeStatus.UNDER_REVIEW,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=150.00),
        seller_response_due_date="2026-11-10T12:00:00Z",
        hours_until_due=216.0,
        allowed_links=["provide-evidence", "accept-claim"],
        internal_state=InternalState.PENDING_APPROVAL,
        recommended_action=RecommendedAction.CONCEDE,
        win_probability=0.25,
        expected_recovery=0.0,
        assigned_operator="operator_sarah",
        customer_notes="Customer note without card data",
    )

    await repo.save_dispute(dispute)
    retrieved = await repo.get_dispute("PP-D-12345")
    assert retrieved is not None
    assert retrieved.dispute_id == "PP-D-12345"
    assert retrieved.dispute_amount.value == 150.00
    assert retrieved.internal_state == InternalState.PENDING_APPROVAL
    assert retrieved.recommended_action == RecommendedAction.CONCEDE

    assert await repo.get_dispute("NON_EXISTENT_DISPUTE") is None


@pytest.mark.asyncio
async def test_order_lookup_by_id_and_save_order(db_conn: aiosqlite.Connection) -> None:
    """Test retrieving order by order_id and saving a new order."""
    repo = MerchantRepository(db_conn)
    order = await repo.get_order_by_id("ORD-1001")
    assert order is not None
    assert order.order_id == "ORD-1001"
    assert await repo.get_order_by_id("NON_EXISTENT_ORDER") is None

    new_order = MerchantOrderRecord(
        order_id="ORD-9999",
        transaction_id="TX-9999",
        buyer_email="buyer99@example.com",
        shipping_address={"country_code": "US", "postal_code": "90210"},
        carrier="DHL",
        tracking_number="DHL1234567890",
        delivery_status="DELIVERED",
        shipped_date="2026-10-22T08:00:00Z",
    )
    await repo.save_order(new_order)
    retrieved_new = await repo.get_order_by_id("ORD-9999")
    assert retrieved_new is not None
    assert retrieved_new.transaction_id == "TX-9999"


@pytest.mark.asyncio
async def test_assemble_evidence_package(db_conn: aiosqlite.Connection) -> None:
    """Test assemble_evidence_package for existing and missing orders."""
    repo = MerchantRepository(db_conn)
    pkg = await repo.assemble_evidence_package("TX-1001")
    assert pkg.record_found is True
    assert pkg.status == "RECORD_FOUND"
    assert pkg.carrier == "USPS"

    missing_pkg = await repo.assemble_evidence_package("TX-MISSING")
    assert missing_pkg.record_found is False
    assert missing_pkg.status == "RECORD_NOT_FOUND"
    assert missing_pkg.order is None


@pytest.mark.asyncio
async def test_dispute_high_value_concede_gate(db_conn: aiosqlite.Connection) -> None:
    """Verify invariant: dispute_amount >= 100 with CONCEDE must be PENDING_APPROVAL."""
    dispute = DisputeRecord(
        dispute_id="PP-D-GATE",
        create_time="2026-11-01T12:00:00Z",
        reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        status=DisputeStatus.UNDER_REVIEW,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=120.00),
        seller_response_due_date="2026-11-10T12:00:00Z",
        hours_until_due=48.0,
        recommended_action=RecommendedAction.CONCEDE,
        internal_state=InternalState.AUTO_READY,  # should be forced to PENDING_APPROVAL
    )
    assert dispute.internal_state == InternalState.PENDING_APPROVAL
