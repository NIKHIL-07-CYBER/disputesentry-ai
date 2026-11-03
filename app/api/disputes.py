"""FastAPI endpoints for dispute management and evidence inspection."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

import aiosqlite
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.config import AppConfig, get_config
from app.storage.database import open_database
from app.storage.repository import MerchantRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Disputes"])


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


@router.get("/api/disputes")
@router.get("/api/v1/disputes", include_in_schema=False)
async def list_disputes(
    db: Annotated[aiosqlite.Connection, Depends(get_db_connection)],
    status_filter: str | None = Query(default=None, alias="status"),
    stage_filter: str | None = Query(default=None, alias="stage"),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> dict[str, Any]:
    """Retrieve paginated dispute records sorted by urgency and amount."""
    query = """
        SELECT dispute_id, create_time, reason, status,
               dispute_life_cycle_stage, dispute_amount_currency,
               dispute_amount_value, seller_response_due_date,
               hours_until_due, allowed_links, internal_state,
               recommended_action, win_probability, expected_recovery,
               assigned_operator, customer_notes
        FROM disputes
        WHERE 1=1
    """
    params: list[Any] = []

    if status_filter:
        query += " AND status = ?"
        params.append(status_filter)
    if stage_filter:
        query += " AND dispute_life_cycle_stage = ?"
        params.append(stage_filter)

    query += " ORDER BY hours_until_due ASC, dispute_amount_value DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    items: list[dict[str, Any]] = []
    async with db.execute(query, tuple(params)) as cursor:
        rows = await cursor.fetchall()
        for row in rows:
            items.append(
                {
                    "dispute_id": str(row[0]),
                    "create_time": str(row[1]),
                    "reason": str(row[2]),
                    "status": str(row[3]),
                    "dispute_stage": str(row[4]),
                    "dispute_amount": {
                        "currency": str(row[5]),
                        "value": float(row[6]),
                    },
                    "seller_response_due_date": str(row[7]),
                    "hours_until_due": float(row[8]),
                    "allowed_links": json.loads(str(row[9])),
                    "decision_state": str(row[10]),
                    "recommended_action": str(row[11]) if row[11] is not None else None,
                    "win_probability": float(row[12]),
                    "expected_net_recovery": float(row[13]),
                    "assigned_operator": str(row[14]) if row[14] is not None else None,
                }
            )

    count_query = "SELECT COUNT(*) FROM disputes WHERE 1=1"
    count_params: list[Any] = []
    if status_filter:
        count_query += " AND status = ?"
        count_params.append(status_filter)
    if stage_filter:
        count_query += " AND dispute_life_cycle_stage = ?"
        count_params.append(stage_filter)

    total = 0
    async with db.execute(count_query, tuple(count_params)) as count_cur:
        count_row = await count_cur.fetchone()
        if count_row is not None:
            total = int(count_row[0])

    return {"items": items, "total": total}


@router.get("/api/disputes/{dispute_id}")
@router.get("/api/v1/disputes/{dispute_id}", include_in_schema=False)
async def get_dispute_detail(
    dispute_id: str,
    db: Annotated[aiosqlite.Connection, Depends(get_db_connection)],
) -> dict[str, Any]:
    """Retrieve complete dispute record, assembled evidence package, and audit history."""
    repo = MerchantRepository(db)
    dispute = await repo.get_dispute(dispute_id)
    if dispute is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dispute not found: {dispute_id}",
        )

    # Fetch audit trail
    audit_entries: list[dict[str, Any]] = []
    async with db.execute(
        """
        SELECT entry_id, timestamp, dispute_id, action, actor, details, prev_hash,
               entry_hash, previous_state, new_state
        FROM audit_log
        WHERE dispute_id = ?
        ORDER BY rowid ASC
        """,
        (dispute_id,),
    ) as cursor:
        rows = await cursor.fetchall()
        for r in rows:
            details_dict: dict[str, Any] = {}
            try:
                raw_details = str(r[5])
                if raw_details:
                    loaded = json.loads(raw_details)
                    if isinstance(loaded, dict):
                        details_dict = loaded
            except Exception:
                details_dict = {}

            audit_entries.append(
                {
                    "entry_id": str(r[0]),
                    "timestamp": str(r[1]),
                    "dispute_id": str(r[2]),
                    "action": str(r[3]),
                    "actor": str(r[4]),
                    "details": details_dict,
                    "prev_hash": str(r[6]),
                    "entry_hash": str(r[7]),
                    "previous_state": str(r[8]) if r[8] is not None else None,
                    "new_state": str(r[9]) if r[9] is not None else None,
                }
            )

    # Assemble evidence package
    pkg = await repo.assemble_evidence_package(dispute_id)
    if not pkg.record_found:
        # Check if an order exists in merchant_orders
        async with db.execute(
            "SELECT transaction_id FROM merchant_orders LIMIT 1"
        ) as cur:
            order_row = await cur.fetchone()
            if order_row and order_row[0]:
                pkg = await repo.assemble_evidence_package(str(order_row[0]))

    return {
        "dispute_id": dispute.dispute_id,
        "create_time": dispute.create_time,
        "reason": dispute.reason.value,
        "status": dispute.status.value,
        "dispute_life_cycle_stage": dispute.dispute_life_cycle_stage.value,
        "dispute_amount": {
            "currency": dispute.dispute_amount.currency,
            "value": dispute.dispute_amount.value,
        },
        "seller_response_due_date": dispute.seller_response_due_date,
        "hours_until_due": dispute.hours_until_due,
        "allowed_links": dispute.allowed_links,
        "internal_state": dispute.internal_state.value,
        "recommended_action": (
            dispute.recommended_action.value if dispute.recommended_action else None
        ),
        "win_probability": dispute.win_probability,
        "expected_recovery": dispute.expected_recovery,
        "assigned_operator": dispute.assigned_operator,
        "customer_notes": dispute.customer_notes,
        "evidence_package": pkg.model_dump(),
        "audit_trail": audit_entries,
    }
