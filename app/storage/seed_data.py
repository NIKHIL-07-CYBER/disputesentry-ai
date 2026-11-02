"""Initial seed orders for local merchant datastore (DSP006)."""

from __future__ import annotations

import json
from typing import Any

import aiosqlite

from app.domain.models import MerchantOrderRecord

SEEDED_ORDERS: list[dict[str, Any]] = [
    {
        "order_id": "ORD-1001",
        "transaction_id": "TX-1001",
        "buyer_email": "buyer1@example.com",
        "shipping_address": {
            "line1": "123 Main St",
            "city": "San Jose",
            "state": "CA",
            "postal_code": "95131",
            "country_code": "US",
        },
        "carrier": "USPS",
        "tracking_number": "9400100000000000000000",
        "delivery_status": "DELIVERED",
        "shipped_date": "2026-10-01T10:00:00Z",
        "delivery_date": "2026-10-05T15:00:00Z",
        "refund_history": [],
    },
    {
        "order_id": "ORD-1002",
        "transaction_id": "TX-1002",
        "buyer_email": "buyer2@example.com",
        "shipping_address": {
            "line1": "456 Market St",
            "city": "Seattle",
            "state": "WA",
            "postal_code": "98101",
            "country_code": "US",
        },
        "carrier": "UPS",
        "tracking_number": "1Z9999999999999999",
        "delivery_status": "IN_TRANSIT",
        "shipped_date": "2026-10-10T12:00:00Z",
        "delivery_date": None,
        "refund_history": [],
    },
    {
        "order_id": "ORD-1003",
        "transaction_id": "TX-1003",
        "buyer_email": "buyer3@example.com",
        "shipping_address": {
            "line1": "789 Broadway",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
            "country_code": "US",
        },
        "carrier": "FEDEX",
        "tracking_number": "794999999999",
        "delivery_status": "SHIPPED",
        "shipped_date": "2026-10-15T09:00:00Z",
        "delivery_date": None,
        "refund_history": [],
    },
    {
        "order_id": "ORD-1006",
        "transaction_id": "TXN-987654321",
        "buyer_email": "buyer@example.com",
        "shipping_address": {
            "line1": "100 Pine St",
            "city": "Austin",
            "state": "TX",
            "postal_code": "78701",
            "country_code": "US",
        },
        "carrier": "USPS",
        "tracking_number": "9400100000000000000001",
        "delivery_status": "DELIVERED",
        "shipped_date": "2026-10-20T10:00:00Z",
        "delivery_date": "2026-10-25T14:30:00Z",
        "refund_history": [],
    },
]


async def seed_merchant_orders(conn: aiosqlite.Connection) -> None:
    """Insert seeded fixture orders if not already present in the database."""
    for order_data in SEEDED_ORDERS:
        order = MerchantOrderRecord(**order_data)
        await conn.execute(
            """
            INSERT OR IGNORE INTO merchant_orders (
                order_id, transaction_id, buyer_email, shipping_address,
                carrier, tracking_number, delivery_status, shipped_date,
                delivery_date, refund_history
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                order.order_id,
                order.transaction_id,
                order.buyer_email,
                json.dumps(order.shipping_address),
                order.carrier,
                order.tracking_number,
                order.delivery_status,
                order.shipped_date,
                order.delivery_date,
                json.dumps(order.refund_history),
            ),
        )
    await conn.commit()
