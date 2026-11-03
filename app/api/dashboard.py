"""FastAPI routes for the Jinja2 merchant operator dashboard."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

import aiosqlite
from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import AppConfig, get_config
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
from app.storage.database import open_database

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Dashboard"])

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


async def get_db_connection(request: Request) -> AsyncIterator[aiosqlite.Connection]:
    """Dependency yielding an active database connection."""
    app_state = getattr(request.app, "state", None)
    if app_state and hasattr(app_state, "db_conn"):
        conn: aiosqlite.Connection = app_state.db_conn
        yield conn
        return

    config_obj = getattr(app_state, "config", None) if app_state else None
    config: AppConfig = config_obj if isinstance(config_obj, AppConfig) else get_config()
    db_path = config.database_url.removeprefix("sqlite+aiosqlite:///")
    async with open_database(db_path) as conn:
        yield conn


@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(
    request: Request,
    db: Annotated[aiosqlite.Connection, Depends(get_db_connection)],
) -> HTMLResponse:
    """Render the priority dispute queue operator dashboard with metrics summary."""
    disputes: list[DisputeRecord] = []

    # Fetch disputes ordered by deadline urgency (hours_until_due ASC)
    # and amount (dispute_amount_value DESC)
    async with db.execute(
        """
        SELECT dispute_id, create_time, reason, status,
               dispute_life_cycle_stage, dispute_amount_currency,
               dispute_amount_value, seller_response_due_date,
               hours_until_due, allowed_links, internal_state,
               recommended_action, win_probability, expected_recovery,
               assigned_operator, customer_notes
        FROM disputes
        ORDER BY hours_until_due ASC, dispute_amount_value DESC
        """
    ) as cursor:
        rows = await cursor.fetchall()
        for row in rows:
            rec_action = (
                RecommendedAction(str(row[11])) if row[11] is not None else None
            )
            disputes.append(
                DisputeRecord(
                    dispute_id=str(row[0]),
                    create_time=str(row[1]),
                    reason=DisputeReason(str(row[2])),
                    status=DisputeStatus(str(row[3])),
                    dispute_life_cycle_stage=DisputeLifeCycleStage(str(row[4])),
                    dispute_amount=Money(
                        currency=str(row[5]),
                        value=float(row[6]),
                    ),
                    seller_response_due_date=str(row[7]),
                    hours_until_due=float(row[8]),
                    allowed_links=json.loads(str(row[9])),
                    internal_state=InternalState(str(row[10])),
                    recommended_action=rec_action,
                    win_probability=float(row[12]),
                    expected_recovery=float(row[13]),
                    assigned_operator=str(row[14]) if row[14] is not None else None,
                    customer_notes=str(row[15]),
                )
            )

    # Compute recovery KPIs
    metrics_svc = MetricsService(db)
    metrics = await metrics_svc.compute_recovery_metrics()

    # Calculate active at-risk amount and pending approval count
    total_at_risk = sum(
        d.dispute_amount.value
        for d in disputes
        if d.internal_state != InternalState.RESOLVED
        and d.status != DisputeStatus.RESOLVED
    )
    pending_approvals = sum(
        1 for d in disputes if d.internal_state == InternalState.PENDING_APPROVAL
    )

    metrics["total_at_risk_usd"] = round(total_at_risk, 2)
    metrics["pending_approvals_count"] = pending_approvals

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "disputes": disputes,
            "metrics": metrics,
        },
    )
