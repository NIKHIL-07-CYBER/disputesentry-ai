"""FastAPI endpoint for dispute win rate and recovery metrics (DSP021)."""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Depends, Request

from app.config import AppConfig, get_config
from app.services.metrics_service import MetricsService
from app.storage.database import open_database

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Metrics"])


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


@router.get("/api/metrics")
@router.get("/api/v1/metrics", include_in_schema=False)
async def get_metrics_summary(
    db: Annotated[aiosqlite.Connection, Depends(get_db_connection)],
) -> dict[str, Any]:
    """Return aggregated win rate, net recovery, and total dollars saved (DSP021)."""
    metrics_svc = MetricsService(db)
    metrics = await metrics_svc.compute_recovery_metrics()

    # Query active/pending numbers for dashboard display
    total_at_risk = 0.0
    pending_approvals = 0

    try:
        async with db.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        CASE
                            WHEN internal_state != 'RESOLVED' AND status != 'RESOLVED'
                            THEN dispute_amount_value
                            ELSE 0.0
                        END
                    ),
                    0.0
                ),
                COALESCE(SUM(CASE WHEN internal_state = 'PENDING_APPROVAL' THEN 1 ELSE 0 END), 0)
            FROM disputes
            """
        ) as cursor:
            row = await cursor.fetchone()
            if row is not None:
                total_at_risk = float(row[0])
                pending_approvals = int(row[1])
    except Exception as exc:
        logger.warning("Failed to query active dispute counts: %s", exc)

    metrics["total_at_risk_usd"] = round(total_at_risk, 2)
    metrics["pending_approvals_count"] = pending_approvals
    return metrics
