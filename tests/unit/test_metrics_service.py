"""Unit tests for the Historical Dispute Recovery Metrics Service (S06, DSP021)."""

from __future__ import annotations

import aiosqlite
import pytest

from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    InternalState,
    Money,
    RecommendedAction,
)
from app.services.metrics_service import MetricsService
from app.storage.database import init_database
from app.storage.repository import MerchantRepository


def test_t06_04_audit_metrics_calculation_ten_disputes() -> None:
    """T06-04 (DSP021): 10 resolved disputes (6 won, 4 lost) -> win_rate=0.60."""
    disputes = [
        {
            "dispute_id": f"D-W{i}",
            "outcome": "RESOLVED_MERCHANT_WON",
            "amount": 100.0,
            "fee_paid": 0.0,
        }
        for i in range(6)
    ] + [
        {
            "dispute_id": f"D-L{j}",
            "outcome": "RESOLVED_BUYER_WON",
            "amount": 50.0,
            "fee_paid": 15.0,
        }
        for j in range(4)
    ]
    # Total disputed = 6*100 + 4*50 = 600 + 200 = 800.0
    # Won count = 6, Lost count = 4, Total = 10 -> win_rate = 0.60
    # Gross recovered = 600.0
    # Fees paid = 4 * 15.0 = 60.0
    # Net recovery = 600.0 - 60.0 = 540.0
    # Net recovery rate = 540.0 / 800.0 = 0.675
    metrics = MetricsService.compute_metrics_from_records(disputes)

    assert metrics["total_concluded"] == 10
    assert metrics["won_count"] == 6
    assert metrics["lost_count"] == 4
    assert metrics["win_rate"] == 0.60
    assert metrics["gross_recovered_usd"] == 600.00
    assert metrics["fees_paid_usd"] == 60.00
    assert metrics["net_recovery_usd"] == 540.00
    assert metrics["net_recovery_rate"] == 0.675
    assert metrics["total_saved_usd"] == 540.00


def test_dsp021_catalog_fixture_good() -> None:
    """Validate DSP021 good fixture dataset matching expected metrics."""
    good_records = [
        {
            "dispute_id": "PP-D-01",
            "outcome": "RESOLVED_MERCHANT_WON",
            "amount": 100.00,
            "fee_paid": 0.00,
        },
        {
            "dispute_id": "PP-D-02",
            "outcome": "RESOLVED_BUYER_WON",
            "amount": 50.00,
            "fee_paid": 20.00,
        },
        {
            "dispute_id": "PP-D-03",
            "outcome": "RESOLVED_MERCHANT_WON",
            "amount": 150.00,
            "fee_paid": 0.00,
        },
    ]
    metrics = MetricsService.compute_metrics_from_records(good_records)

    assert metrics["total_concluded"] == 3
    assert metrics["won_count"] == 2
    assert metrics["lost_count"] == 1
    assert metrics["win_rate"] == 0.667
    assert metrics["gross_recovered_usd"] == 250.00
    assert metrics["fees_paid_usd"] == 20.00
    assert metrics["net_recovery_usd"] == 230.00


def test_dsp021_catalog_fixture_bad_empty() -> None:
    """Validate DSP021 bad fixture (empty resolved disputes) handles zeros safely."""
    metrics = MetricsService.compute_metrics_from_records([])

    assert metrics["total_concluded"] == 0
    assert metrics["won_count"] == 0
    assert metrics["lost_count"] == 0
    assert metrics["win_rate"] == 0.00
    assert metrics["gross_recovered_usd"] == 0.00
    assert metrics["fees_paid_usd"] == 0.00
    assert metrics["net_recovery_usd"] == 0.00
    assert metrics["net_recovery_rate"] == 0.00
    assert metrics["total_saved_usd"] == 0.00


def test_all_won_disputes() -> None:
    """100% win rate when all disputes are won and 0 fees paid."""
    records = [
        {"dispute_id": "D-1", "outcome": "RESOLVED_MERCHANT_WON", "amount": 200.0, "fee_paid": 0.0},
        {"dispute_id": "D-2", "outcome": "RESOLVED_MERCHANT_WON", "amount": 300.0, "fee_paid": 0.0},
    ]
    metrics = MetricsService.compute_metrics_from_records(records)

    assert metrics["total_concluded"] == 2
    assert metrics["won_count"] == 2
    assert metrics["lost_count"] == 0
    assert metrics["win_rate"] == 1.00
    assert metrics["net_recovery_usd"] == 500.00
    assert metrics["net_recovery_rate"] == 1.00


def test_all_lost_disputes() -> None:
    """0% win rate and negative net recovery when disputes are conceded or lost."""
    records = [
        {"dispute_id": "D-1", "outcome": "RESOLVED_BUYER_WON", "amount": 50.0, "fee_paid": 20.0},
        {"dispute_id": "D-2", "outcome": "RESOLVED_BUYER_WON", "amount": 75.0, "fee_paid": 20.0},
    ]
    metrics = MetricsService.compute_metrics_from_records(records)

    assert metrics["total_concluded"] == 2
    assert metrics["won_count"] == 0
    assert metrics["lost_count"] == 2
    assert metrics["win_rate"] == 0.00
    assert metrics["gross_recovered_usd"] == 0.00
    assert metrics["fees_paid_usd"] == 40.00
    assert metrics["net_recovery_usd"] == -40.00


@pytest.mark.asyncio
async def test_compute_recovery_metrics_no_db_connection() -> None:
    """MetricsService with db=None returns empty metrics safely."""
    service = MetricsService(db_conn=None)
    metrics = await service.compute_recovery_metrics()
    assert metrics["total_concluded"] == 0
    assert metrics["win_rate"] == 0.00


@pytest.mark.asyncio
async def test_compute_recovery_metrics_from_database_plain_notes() -> None:
    """MetricsService correctly falls back when customer_notes is plain text or invalid JSON."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)

        d1 = DisputeRecord(
            dispute_id="PP-D-CONCEDED-01",
            create_time="2026-10-25T10:00:00Z",
            reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
            status=DisputeStatus.RESOLVED,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency="USD", value=60.0),
            seller_response_due_date="2026-11-05T10:00:00Z",
            internal_state=InternalState.RESOLVED,
            recommended_action=RecommendedAction.CONCEDE,
            win_probability=0.10,
            expected_recovery=0.0,
            customer_notes="Customer conceded after discussion.",
        )
        d2 = DisputeRecord(
            dispute_id="PP-D-CONTESTED-02",
            create_time="2026-10-26T10:00:00Z",
            reason=DisputeReason.UNAUTHORISED,
            status=DisputeStatus.RESOLVED,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency="USD", value=90.0),
            seller_response_due_date="2026-11-06T10:00:00Z",
            internal_state=InternalState.RESOLVED,
            recommended_action=RecommendedAction.CONTEST,
            win_probability=0.90,
            expected_recovery=90.0,
            customer_notes="{invalid_json: true}",
        )
        await repo.save_dispute(d1)
        await repo.save_dispute(d2)

        service = MetricsService(db)
        metrics = await service.compute_recovery_metrics()

        assert metrics["total_concluded"] == 2
        assert metrics["won_count"] == 1
        assert metrics["lost_count"] == 1
        assert metrics["win_rate"] == 0.50
        assert metrics["gross_recovered_usd"] == 90.00
        assert metrics["fees_paid_usd"] == 15.00
        assert metrics["net_recovery_usd"] == 75.00

    """MetricsService queries database and aggregates resolved disputes correctly."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        repo = MerchantRepository(db)

        # Insert 3 disputes: 2 resolved (1 won, 1 lost) and 1 still open
        d1 = DisputeRecord(
            dispute_id="PP-D-RES-01",
            create_time="2026-10-25T10:00:00Z",
            reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
            status=DisputeStatus.RESOLVED,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency="USD", value=120.0),
            seller_response_due_date="2026-11-05T10:00:00Z",
            internal_state=InternalState.RESOLVED,
            recommended_action=RecommendedAction.CONTEST,
            win_probability=0.90,
            expected_recovery=120.0,
            customer_notes='{"outcome": "RESOLVED_MERCHANT_WON", "fee_paid": 0.0}',
        )
        d2 = DisputeRecord(
            dispute_id="PP-D-RES-02",
            create_time="2026-10-26T10:00:00Z",
            reason=DisputeReason.UNAUTHORISED,
            status=DisputeStatus.RESOLVED,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency="USD", value=40.0),
            seller_response_due_date="2026-11-06T10:00:00Z",
            internal_state=InternalState.RESOLVED,
            recommended_action=RecommendedAction.CONCEDE,
            win_probability=0.10,
            expected_recovery=0.0,
            customer_notes='{"outcome": "RESOLVED_BUYER_WON", "fee_paid": 20.0}',
        )
        d3_open = DisputeRecord(
            dispute_id="PP-D-OPEN-03",
            create_time="2026-10-27T10:00:00Z",
            reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
            status=DisputeStatus.UNDER_REVIEW,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency="USD", value=200.0),
            seller_response_due_date="2026-11-07T10:00:00Z",
            internal_state=InternalState.AUTO_READY,
            recommended_action=RecommendedAction.CONTEST,
            win_probability=0.85,
            expected_recovery=160.0,
        )
        await repo.save_dispute(d1)
        await repo.save_dispute(d2)
        await repo.save_dispute(d3_open)

        service = MetricsService(db)
        metrics = await service.compute_recovery_metrics()

        assert metrics["total_concluded"] == 2
        assert metrics["won_count"] == 1
        assert metrics["lost_count"] == 1
        assert metrics["win_rate"] == 0.50
        assert metrics["gross_recovered_usd"] == 120.00
        assert metrics["fees_paid_usd"] == 20.00
        assert metrics["net_recovery_usd"] == 100.00
        assert metrics["total_saved_usd"] == 100.00
