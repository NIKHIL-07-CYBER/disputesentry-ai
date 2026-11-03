"""Historical Dispute Recovery Metrics Service for DisputeSentry AI (DSP021).

Calculates win rate vs net recovery, gross recovered dollars, dispute fee penalties,
and net recovery rate across the dispute lifecycle.
"""

from __future__ import annotations

import json
from typing import Any

import aiosqlite


class MetricsService:
    """Historical audit metrics service computing win rate and net recovery (DSP021)."""

    def __init__(self, db_conn: aiosqlite.Connection | None = None) -> None:
        self.db = db_conn

    @staticmethod
    def compute_metrics_from_records(records: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute recovery KPIs from a list of concluded dispute records.

        Args:
            records: List of dictionaries with dispute outcome, amount, and fee_paid.

        Returns:
            Dictionary containing total_concluded, won_count, lost_count, win_rate,
            gross_recovered_usd, fees_paid_usd, net_recovery_usd, and net_recovery_rate.
        """
        total_concluded = len(records)
        if total_concluded == 0:
            return {
                "total_concluded": 0,
                "won_count": 0,
                "lost_count": 0,
                "win_rate": 0.00,
                "gross_recovered_usd": 0.00,
                "fees_paid_usd": 0.00,
                "net_recovery_usd": 0.00,
                "net_recovery_rate": 0.00,
                "total_saved_usd": 0.00,
                "total_disputed_usd": 0.00,
                "fees_avoided_usd": 0.00,
            }

        won_count = 0
        lost_count = 0
        gross_recovered = 0.0
        fees_paid = 0.0
        total_disputed = 0.0

        for rec in records:
            outcome = str(rec.get("outcome", "")).upper()
            amt = float(
                rec.get(
                    "amount",
                    rec.get("dispute_amount_value", rec.get("dispute_amount", 0.0)),
                )
            )
            fee = float(rec.get("fee_paid", rec.get("dispute_fee", 0.0)))
            total_disputed += amt

            is_won = (
                "MERCHANT_WON" in outcome
                or "SELLER_FAVOUR" in outcome
                or outcome in ("WON", "SELLER_WON")
            )

            if is_won:
                won_count += 1
                gross_recovered += amt
            else:
                lost_count += 1
                fees_paid += fee

        win_rate = round(won_count / total_concluded, 3)
        gross_recovered = round(gross_recovered, 2)
        fees_paid = round(fees_paid, 2)
        net_recovery = round(gross_recovered - fees_paid, 2)
        net_rate = (
            round(net_recovery / total_disputed, 4) if total_disputed > 0.0 else 0.0
        )

        return {
            "total_concluded": total_concluded,
            "won_count": won_count,
            "lost_count": lost_count,
            "win_rate": win_rate,
            "gross_recovered_usd": gross_recovered,
            "fees_paid_usd": fees_paid,
            "net_recovery_usd": net_recovery,
            "net_recovery_rate": net_rate,
            "total_saved_usd": net_recovery,
            "total_disputed_usd": round(total_disputed, 2),
            "fees_avoided_usd": round(won_count * 15.0, 2),
        }

    async def compute_recovery_metrics(self) -> dict[str, Any]:
        """Query resolved disputes from SQLite and compute net recovery metrics.

        Returns:
            Dictionary with aggregated recovery metrics.
        """
        if self.db is None:
            return self.compute_metrics_from_records([])

        records: list[dict[str, Any]] = []
        async with self.db.execute(
            """
            SELECT dispute_id, status, dispute_amount_value, internal_state,
                   recommended_action, customer_notes
            FROM disputes
            WHERE status = 'RESOLVED' OR internal_state = 'RESOLVED'
            """
        ) as cursor:
            rows = await cursor.fetchall()

        for row in rows:
            dispute_id = str(row[0])
            amount = float(row[2])
            notes = str(row[5]) if row[5] is not None else ""

            outcome = "RESOLVED_MERCHANT_WON"
            fee_paid = 0.0

            # Attempt parsing JSON outcome from customer_notes
            if notes.strip().startswith("{") and notes.strip().endswith("}"):
                try:
                    payload = json.loads(notes)
                    if isinstance(payload, dict):
                        outcome = str(payload.get("outcome", outcome))
                        fee_paid = float(payload.get("fee_paid", fee_paid))
                except Exception:
                    pass
            else:
                # Default inference based on recommended_action
                rec_action = str(row[4]) if row[4] is not None else ""
                if rec_action == "CONCEDE":
                    outcome = "RESOLVED_BUYER_WON"
                    fee_paid = 15.0

            records.append(
                {
                    "dispute_id": dispute_id,
                    "outcome": outcome,
                    "amount": amount,
                    "fee_paid": fee_paid,
                }
            )

        return self.compute_metrics_from_records(records)
