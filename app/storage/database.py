"""SQLite database connection and schema management with WAL mode (DSP022)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS merchant_orders (
    order_id TEXT PRIMARY KEY,
    transaction_id TEXT UNIQUE NOT NULL,
    buyer_email TEXT NOT NULL,
    shipping_address TEXT NOT NULL,
    carrier TEXT NOT NULL,
    tracking_number TEXT NOT NULL,
    delivery_status TEXT NOT NULL,
    shipped_date TEXT NOT NULL,
    delivery_date TEXT,
    refund_history TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS disputes (
    dispute_id TEXT PRIMARY KEY,
    create_time TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL,
    dispute_life_cycle_stage TEXT NOT NULL,
    dispute_amount_currency TEXT NOT NULL,
    dispute_amount_value REAL NOT NULL,
    seller_response_due_date TEXT NOT NULL,
    hours_until_due REAL NOT NULL DEFAULT 0.0,
    allowed_links TEXT NOT NULL DEFAULT '[]',
    internal_state TEXT NOT NULL,
    recommended_action TEXT,
    win_probability REAL NOT NULL DEFAULT 0.0,
    expected_recovery REAL NOT NULL DEFAULT 0.0,
    assigned_operator TEXT,
    customer_notes TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_log (
    entry_id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    dispute_id TEXT NOT NULL,
    action TEXT NOT NULL,
    actor TEXT NOT NULL,
    details TEXT NOT NULL,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL,
    previous_state TEXT,
    new_state TEXT,
    actor_id TEXT,
    payload_summary TEXT
);

CREATE TRIGGER IF NOT EXISTS prevent_audit_log_update
BEFORE UPDATE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: updates not permitted');
END;

CREATE TRIGGER IF NOT EXISTS prevent_audit_log_delete
BEFORE DELETE ON audit_log
BEGIN
    SELECT RAISE(ABORT, 'AUDIT_LOG_IMMUTABLE: deletes not permitted');
END;
"""


async def init_database(conn: aiosqlite.Connection) -> None:
    """Initialize database schemas, indices, and append-only immutability triggers."""
    await conn.executescript(SCHEMA_SQL)
    await conn.commit()


@asynccontextmanager
async def open_database(
    db_path: str | Path = "disputesentry.db",
) -> AsyncIterator[aiosqlite.Connection]:
    """Provide an asynchronous context manager for SQLite database connection."""
    async with aiosqlite.connect(str(db_path)) as conn:
        await init_database(conn)
        yield conn
