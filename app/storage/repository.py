"""Repository for merchant orders and dispute records (DSP006)."""

from __future__ import annotations

import json

import aiosqlite

from app.domain.exceptions import OrderNotFoundError
from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    InternalState,
    MerchantEvidencePackage,
    MerchantOrderRecord,
    Money,
    RecommendedAction,
)


class MerchantRepository:
    """Repository handling persistence and retrieval of merchant orders and disputes."""

    def __init__(self, db_conn: aiosqlite.Connection) -> None:
        self.db = db_conn

    async def get_order_by_transaction(self, tx_id: str) -> MerchantOrderRecord | None:
        """Fetch merchant order record matching the PayPal transaction_id."""
        async with self.db.execute(
            """
            SELECT order_id, transaction_id, buyer_email, shipping_address,
                   carrier, tracking_number, delivery_status, shipped_date,
                   delivery_date, refund_history
            FROM merchant_orders
            WHERE transaction_id = ?
            """,
            (tx_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        shipping_address = json.loads(str(row[3]))
        refund_history = json.loads(str(row[9]))

        return MerchantOrderRecord(
            order_id=str(row[0]),
            transaction_id=str(row[1]),
            buyer_email=str(row[2]),
            shipping_address=shipping_address,
            carrier=str(row[4]),
            tracking_number=str(row[5]),
            delivery_status=str(row[6]),
            shipped_date=str(row[7]),
            delivery_date=str(row[8]) if row[8] is not None else None,
            refund_history=refund_history,
        )

    async def get_order(self, tx_id: str) -> MerchantOrderRecord:
        """Fetch merchant order or raise OrderNotFoundError if missing."""
        order = await self.get_order_by_transaction(tx_id)
        if order is None:
            raise OrderNotFoundError(f"Order not found for transaction: {tx_id}")
        return order

    async def get_order_by_id(self, order_id: str) -> MerchantOrderRecord | None:
        """Fetch merchant order by its internal order_id."""
        async with self.db.execute(
            """
            SELECT order_id, transaction_id, buyer_email, shipping_address,
                   carrier, tracking_number, delivery_status, shipped_date,
                   delivery_date, refund_history
            FROM merchant_orders
            WHERE order_id = ?
            """,
            (order_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        return MerchantOrderRecord(
            order_id=str(row[0]),
            transaction_id=str(row[1]),
            buyer_email=str(row[2]),
            shipping_address=json.loads(str(row[3])),
            carrier=str(row[4]),
            tracking_number=str(row[5]),
            delivery_status=str(row[6]),
            shipped_date=str(row[7]),
            delivery_date=str(row[8]) if row[8] is not None else None,
            refund_history=json.loads(str(row[9])),
        )

    async def save_order(self, order: MerchantOrderRecord) -> None:
        """Insert or replace a merchant order record."""
        await self.db.execute(
            """
            INSERT OR REPLACE INTO merchant_orders (
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
        await self.db.commit()

    async def assemble_evidence_package(self, tx_id: str) -> MerchantEvidencePackage:
        """Query store and assemble evidence package for a transaction (DSP006)."""
        order = await self.get_order_by_transaction(tx_id)
        if order is None:
            return MerchantEvidencePackage(
                order=None,
                record_found=False,
                status="RECORD_NOT_FOUND",
            )

        return MerchantEvidencePackage(
            order=order,
            carrier=order.carrier,
            shipment_status=order.delivery_status,
            tracking_number=order.tracking_number,
            customer_notes=[],
            record_found=True,
            status="RECORD_FOUND",
        )

    async def save_dispute(self, dispute: DisputeRecord) -> None:
        """Persist or update a DisputeRecord in the database."""
        await self.db.execute(
            """
            INSERT OR REPLACE INTO disputes (
                dispute_id, create_time, reason, status,
                dispute_life_cycle_stage, dispute_amount_currency,
                dispute_amount_value, seller_response_due_date,
                hours_until_due, allowed_links, internal_state,
                recommended_action, win_probability, expected_recovery,
                assigned_operator, customer_notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dispute.dispute_id,
                dispute.create_time,
                dispute.reason.value,
                dispute.status.value,
                dispute.dispute_life_cycle_stage.value,
                dispute.dispute_amount.currency,
                dispute.dispute_amount.value,
                dispute.seller_response_due_date,
                dispute.hours_until_due,
                json.dumps(dispute.allowed_links),
                dispute.internal_state.value,
                dispute.recommended_action.value if dispute.recommended_action else None,
                dispute.win_probability,
                dispute.expected_recovery,
                dispute.assigned_operator,
                dispute.customer_notes,
            ),
        )
        await self.db.commit()

    async def get_dispute(self, dispute_id: str) -> DisputeRecord | None:
        """Retrieve a DisputeRecord by its dispute_id."""
        async with self.db.execute(
            """
            SELECT dispute_id, create_time, reason, status,
                   dispute_life_cycle_stage, dispute_amount_currency,
                   dispute_amount_value, seller_response_due_date,
                   hours_until_due, allowed_links, internal_state,
                   recommended_action, win_probability, expected_recovery,
                   assigned_operator, customer_notes
            FROM disputes
            WHERE dispute_id = ?
            """,
            (dispute_id,),
        ) as cursor:
            row = await cursor.fetchone()

        if row is None:
            return None

        recommended_action = (
            RecommendedAction(str(row[11])) if row[11] is not None else None
        )

        return DisputeRecord(
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
            recommended_action=recommended_action,
            win_probability=float(row[12]),
            expected_recovery=float(row[13]),
            assigned_operator=str(row[14]) if row[14] is not None else None,
            customer_notes=str(row[15]),
        )
