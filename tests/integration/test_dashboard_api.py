"""Integration tests for Merchant Operator Dashboard and Web API (S10).

Covers:
- T10-01: Dashboard HTML page load
- T10-02: Queue sorting by urgency and amount
- T10-03: Dispute detail modal inspection and 404 error handling
- T10-04: Metrics summary endpoint
- Positive and boundary cases (approvals, rejections, empty state, XSS auto-escaping)
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import aiosqlite
import pytest
from httpx import ASGITransport, AsyncClient

from app.clients.paypal_client import PayPalDisputesClient
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
from app.main import create_app
from app.services.approval_gate import ApprovalGateService
from app.services.audit_service import AuditService
from app.storage.database import init_database
from app.storage.repository import MerchantRepository


def make_dispute(
    dispute_id: str,
    amount: float,
    hours_until_due: float,
    internal_state: InternalState = InternalState.PENDING_APPROVAL,
    status: DisputeStatus = DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
    customer_notes: str = "",
) -> DisputeRecord:
    """Helper creating dispute records with varying amounts and deadlines."""
    return DisputeRecord(
        dispute_id=dispute_id,
        reason=DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        status=status,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=amount),
        seller_response_due_date="2026-11-15T00:00:00Z",
        hours_until_due=hours_until_due,
        allowed_links=["provide-evidence", "accept-claim"],
        internal_state=internal_state,
        recommended_action=RecommendedAction.CONTEST,
        win_probability=0.85,
        expected_recovery=round(amount * 0.85, 2),
        customer_notes=customer_notes,
    )


@pytest.fixture
async def test_db() -> AsyncGenerator[aiosqlite.Connection, None]:
    """In-memory SQLite test database fixture."""
    async with aiosqlite.connect(":memory:") as db:
        await init_database(db)
        yield db


@pytest.fixture
async def dashboard_client(
    test_db: aiosqlite.Connection,
) -> AsyncGenerator[AsyncClient, None]:
    """Async HTTP client wired to an app using test_db and gate service."""
    application = create_app()
    application.state.db_conn = test_db

    repo = MerchantRepository(test_db)
    audit = AuditService(test_db)
    client = PayPalDisputesClient(
        client_id="mock_client",
        client_secret="mock_secret",
        base_url="https://api-m.sandbox.paypal.com",
    )
    application.state.approval_gate_service = ApprovalGateService(
        repo=repo,
        client=client,
        audit=audit,
    )

    async with AsyncClient(
        transport=ASGITransport(app=application),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_t10_01_dashboard_html_page_load(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """T10-01: Dashboard HTML page load returns HTTP 200, text/html, DisputeSentry AI."""
    repo = MerchantRepository(test_db)
    await repo.save_dispute(
        make_dispute("PP-D-INIT", amount=50.0, hours_until_due=24.0)
    )

    response = await dashboard_client.get("/dashboard")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "DisputeSentry AI" in response.text
    assert "Dispute ID" in response.text
    assert "Priority Dispute Queue" in response.text


@pytest.mark.asyncio
async def test_t10_02_queue_sorting_by_urgency_and_amount(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """T10-02: Queue sorted by hours_until_due ASC and dispute_amount DESC."""
    repo = MerchantRepository(test_db)
    # Seed disputes in scrambled order
    d1 = make_dispute("PP-D-MEDIUM-DUE", amount=100.0, hours_until_due=48.0)
    d2 = make_dispute("PP-D-URGENT-LOW", amount=50.0, hours_until_due=12.0)
    d3 = make_dispute("PP-D-URGENT-HIGH", amount=200.0, hours_until_due=12.0)
    d4 = make_dispute("PP-D-RELAXED", amount=300.0, hours_until_due=72.0)

    for d in [d1, d2, d3, d4]:
        await repo.save_dispute(d)

    response = await dashboard_client.get("/dashboard")
    assert response.status_code == 200
    html = response.text

    # Expected order: d3 (12h, $200), d2 (12h, $50), d1 (48h, $100), d4 (72h, $300)
    idx_d3 = html.find("PP-D-URGENT-HIGH")
    idx_d2 = html.find("PP-D-URGENT-LOW")
    idx_d1 = html.find("PP-D-MEDIUM-DUE")
    idx_d4 = html.find("PP-D-RELAXED")

    assert idx_d3 != -1 and idx_d2 != -1 and idx_d1 != -1 and idx_d4 != -1
    assert idx_d3 < idx_d2 < idx_d1 < idx_d4


@pytest.mark.asyncio
async def test_t10_03_dispute_detail_modal_inspection(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """T10-03: GET /api/disputes/{id} returns JSON with audit trail and evidence package."""
    repo = MerchantRepository(test_db)
    audit = AuditService(test_db)

    # Seed order and dispute
    order = MerchantOrderRecord(
        order_id="ORD-1001",
        transaction_id="TX-1001",
        buyer_email="buyer@example.com",
        shipping_address={
            "line1": "123 Main St",
            "city": "Beverly Hills",
            "state": "CA",
            "postal_code": "90210",
            "country_code": "US",
        },
        carrier="USPS",
        tracking_number="9400100000000000000001",
        delivery_status="DELIVERED",
        shipped_date="2026-10-25T10:00:00Z",
        delivery_date="2026-10-28T14:30:00Z",
        refund_history=[],
    )
    await repo.save_order(order)

    dispute = make_dispute("PP-D-DETAIL-1001", amount=120.0, hours_until_due=10.0)
    await repo.save_dispute(dispute)

    # Seed audit entry
    await audit.log_action(
        dispute_id="PP-D-DETAIL-1001",
        action="EVALUATION_COMPLETED",
        actor="system",
        details={"recommendation": "CONTEST", "confidence": 0.85},
    )

    response = await dashboard_client.get("/api/disputes/PP-D-DETAIL-1001")
    assert response.status_code == 200
    data = response.json()

    assert data["dispute_id"] == "PP-D-DETAIL-1001"
    assert "evidence_package" in data
    assert "audit_trail" in data
    assert len(data["audit_trail"]) >= 1
    assert data["audit_trail"][0]["action"] == "EVALUATION_COMPLETED"


@pytest.mark.asyncio
async def test_t10_03_nonexistent_dispute_returns_404(
    dashboard_client: AsyncClient,
) -> None:
    """Negative case: Non-existent dispute ID returns 404 with error detail."""
    response = await dashboard_client.get("/api/disputes/NON-EXISTENT-ID")
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data or "error" in data


@pytest.mark.asyncio
async def test_t10_04_metrics_summary_endpoint(
    dashboard_client: AsyncClient,
) -> None:
    """T10-04: GET /api/metrics returns win_rate, net_recovery_rate, and total_saved_usd."""
    response = await dashboard_client.get("/api/metrics")
    assert response.status_code == 200
    data = response.json()

    assert "win_rate" in data
    assert "net_recovery_rate" in data
    assert "total_saved_usd" in data
    assert isinstance(data["win_rate"], int | float)
    assert isinstance(data["net_recovery_rate"], int | float)
    assert isinstance(data["total_saved_usd"], int | float)


@pytest.mark.asyncio
async def test_positive_approve_action_from_dashboard(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """Positive case: Approving a dispute updates status to DISPATCHED."""
    repo = MerchantRepository(test_db)
    dispute = make_dispute(
        "PP-D-APPROVE-TEST",
        amount=150.0,
        hours_until_due=36.0,
        internal_state=InternalState.PENDING_APPROVAL,
    )
    await repo.save_dispute(dispute)

    approve_resp = await dashboard_client.post(
        "/api/disputes/PP-D-APPROVE-TEST/approve",
        json={"operator_id": "operator_test", "notes": "Approved from UI"},
    )
    assert approve_resp.status_code == 200
    data = approve_resp.json()
    assert data["internal_state"] == "DISPATCHED"

    # Verify persisted state
    updated = await repo.get_dispute("PP-D-APPROVE-TEST")
    assert updated is not None
    assert updated.internal_state == InternalState.DISPATCHED


@pytest.mark.asyncio
async def test_positive_reject_action_from_dashboard(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """Positive case: Rejecting a dispute updates status to REJECTED."""
    repo = MerchantRepository(test_db)
    dispute = make_dispute(
        "PP-D-REJECT-TEST",
        amount=150.0,
        hours_until_due=36.0,
        internal_state=InternalState.PENDING_APPROVAL,
    )
    await repo.save_dispute(dispute)

    reject_resp = await dashboard_client.post(
        "/api/disputes/PP-D-REJECT-TEST/reject",
        json={"operator_id": "operator_test", "reason": "Operator rejected"},
    )
    assert reject_resp.status_code == 200
    data = reject_resp.json()
    assert data["internal_state"] == "REJECTED"


@pytest.mark.asyncio
async def test_boundary_empty_queue_renders_empty_state(
    dashboard_client: AsyncClient,
) -> None:
    """Boundary case: Empty queue renders 'No active disputes pending' banner."""
    response = await dashboard_client.get("/dashboard")
    assert response.status_code == 200
    assert "No active disputes pending" in response.text


@pytest.mark.asyncio
async def test_security_xss_escaping_in_dashboard(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """Security check: Script tags in customer notes must be auto-escaped in Jinja2."""
    repo = MerchantRepository(test_db)
    xss_payload = "<script>alert('XSS_TEST')</script>"
    dispute = make_dispute(
        "PP-D-XSS-TEST",
        amount=88.0,
        hours_until_due=5.0,
        customer_notes=xss_payload,
    )
    await repo.save_dispute(dispute)

    response = await dashboard_client.get("/dashboard")
    assert response.status_code == 200
    assert "<script>alert('XSS_TEST')</script>" not in response.text
    escaped_needle = "&lt;script&gt;alert(&#39;XSS_TEST&#39;)&lt;/script&gt;"
    assert escaped_needle in response.text or "&lt;script&gt;" in response.text


@pytest.mark.asyncio
async def test_list_disputes_api(
    dashboard_client: AsyncClient, test_db: aiosqlite.Connection
) -> None:
    """Dispute list API returns paginated items and total."""
    repo = MerchantRepository(test_db)
    await repo.save_dispute(make_dispute("PP-D-L1", amount=40.0, hours_until_due=10.0))
    await repo.save_dispute(make_dispute("PP-D-L2", amount=80.0, hours_until_due=20.0))

    response = await dashboard_client.get("/api/disputes")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert data["total"] >= 2


@pytest.mark.asyncio
async def test_static_assets_served(dashboard_client: AsyncClient) -> None:
    """Verify static assets are properly mounted and served."""
    css_resp = await dashboard_client.get("/static/css/style.css")
    assert css_resp.status_code == 200
    assert "DisputeSentry AI" in css_resp.text

    js_resp = await dashboard_client.get("/static/js/app.js")
    assert js_resp.status_code == 200
    assert "openDisputeModal" in js_resp.text

