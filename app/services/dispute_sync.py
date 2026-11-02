"""Dispute synchronization coordinator, HATEOAS action validation, and deadline tracker."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from app.clients.paypal_client import PayPalDisputesClient
from app.domain.exceptions import DisputeSentryError
from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    InternalState,
    Money,
    RecommendedAction,
)
from app.services.audit_service import AuditService
from app.storage.repository import MerchantRepository

logger = logging.getLogger(__name__)


class HATEOASViolationError(DisputeSentryError):
    """Raised when an action is not permitted by dispute HATEOAS links (DSP005)."""

    def __init__(
        self,
        message: str = "Action 'provide_evidence' not permitted",
        error_code: str = "ACTION_NOT_PERMITTED",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class DisputeExpiredError(DisputeSentryError):
    """Raised when an action is attempted on an expired dispute (DSP010)."""

    def __init__(
        self,
        message: str = "Dispute response deadline has expired",
        error_code: str = "DEADLINE_EXPIRED",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


def validate_hateoas_action(
    links: list[dict[str, Any]] | list[Any],
    action: str = "provide_evidence",
) -> bool:
    """Validate whether the specified action is present in dispute HATEOAS links array."""
    target_norm = action.lower().replace("-", "_")
    for link in links:
        if isinstance(link, dict):
            rel = str(link.get("rel", "")).lower().replace("-", "_")
            if rel == target_norm:
                return True
        elif isinstance(link, str):
            rel = link.lower().replace("-", "_")
            if rel == target_norm:
                return True
    return False


def validate_hateoas_action_or_raise(
    links: list[dict[str, Any]] | list[Any],
    action: str = "provide_evidence",
) -> None:
    """Validate action link or raise HATEOASViolationError if absent (DSP005)."""
    if not validate_hateoas_action(links, action):
        logger.warning(
            "HATEOAS link missing for action: action=%s available_links=%s",
            action,
            links,
        )
        raise HATEOASViolationError(
            f"Action '{action}' not permitted",
            error_code="ACTION_NOT_PERMITTED",
        )


class DisputeSyncCoordinator:
    """Coordinates dispute synchronization, evidence assembly, urgency tracking, and dispatch."""

    def __init__(
        self,
        client: PayPalDisputesClient,
        repo: MerchantRepository,
        audit: AuditService,
    ) -> None:
        self.client = client
        self.repo = repo
        self.audit = audit

    def compute_deadline_urgency(
        self,
        due_date_iso: str,
        current_time_iso: str | None = None,
    ) -> tuple[float, str]:
        """Compute remaining hours until seller_response_due_date and urgency tier (DSP010).

        Tiers:
        - <= 0.0 hours: EXPIRED
        - <= 24.0 hours: CRITICAL
        - <= 72.0 hours: MEDIUM
        - > 72.0 hours: LOW
        """
        if not due_date_iso:
            return 0.0, "UNKNOWN"

        clean_due = due_date_iso.replace("Z", "+00:00")
        due_dt = datetime.fromisoformat(clean_due)
        if due_dt.tzinfo is None:
            due_dt = due_dt.replace(tzinfo=UTC)

        if current_time_iso:
            clean_curr = current_time_iso.replace("Z", "+00:00")
            current_dt = datetime.fromisoformat(clean_curr)
            if current_dt.tzinfo is None:
                current_dt = current_dt.replace(tzinfo=UTC)
        else:
            current_dt = datetime.now(UTC)

        diff_seconds = (due_dt - current_dt).total_seconds()
        hours_remaining = round(diff_seconds / 3600.0, 1)

        if hours_remaining <= 0.0:
            urgency_tier = "EXPIRED"
        elif hours_remaining <= 24.0:
            urgency_tier = "CRITICAL"
        elif hours_remaining <= 72.0:
            urgency_tier = "MEDIUM"
        else:
            urgency_tier = "LOW"

        return hours_remaining, urgency_tier

    async def handle_dispute_event(self, webhook_resource: dict[str, Any]) -> DisputeRecord:
        """Process dispute event: validate HATEOAS, match order, calculate urgency, dispatch."""
        dispute_id = webhook_resource.get("dispute_id")
        if not dispute_id or not isinstance(dispute_id, str):
            raise ValueError("Missing or invalid 'dispute_id' in webhook resource")

        # 1. Calculate deadline urgency from seller_response_due_date
        due_date_iso = webhook_resource.get("seller_response_due_date")
        if due_date_iso:
            hours_until_due, urgency_tier = self.compute_deadline_urgency(due_date_iso)
            if hours_until_due <= 0:
                raise DisputeExpiredError(
                    f"Dispute {dispute_id} response deadline has expired",
                    error_code="DEADLINE_EXPIRED",
                )
        else:
            hours_until_due, urgency_tier = 0.0, "UNKNOWN"

        # 2. Extract transaction ID to match local merchant order
        tx_id: str | None = None
        disputed_txs = webhook_resource.get("disputed_transactions")
        if isinstance(disputed_txs, list) and len(disputed_txs) > 0:
            first_tx = disputed_txs[0]
            if isinstance(first_tx, dict):
                tx_id = (
                    first_tx.get("seller_transaction_id")
                    or first_tx.get("transaction_id")
                    or first_tx.get("buyer_transaction_id")
                )
        if not tx_id:
            tx_id = (
                webhook_resource.get("transaction_id")
                or webhook_resource.get("seller_transaction_id")
            )

        evidence_pkg = None
        if tx_id:
            evidence_pkg = await self.repo.assemble_evidence_package(tx_id)

        # 3. Validate HATEOAS link before dispatching mutation (DSP005)
        raw_links = webhook_resource.get("links")
        links: list[dict[str, Any]] = raw_links if isinstance(raw_links, list) else []
        validate_hateoas_action_or_raise(links, "provide_evidence")

        # 4. Assemble carrier evidence package and dispatch to PayPal API (DSP014)
        carrier = (
            evidence_pkg.carrier
            if evidence_pkg and evidence_pkg.carrier
            else "USPS"
        )
        tracking = (
            evidence_pkg.tracking_number
            if evidence_pkg and evidence_pkg.tracking_number
            else ""
        )
        shipment_status = (
            evidence_pkg.shipment_status
            if evidence_pkg and evidence_pkg.shipment_status
            else "DELIVERED"
        )

        notes = (
            f"Item shipped via {carrier} with tracking {tracking}. "
            f"Delivery status: {shipment_status}."
        )
        evidence_payload = {
            "evidence_type": "PROOF_OF_FULFILLMENT",
            "carrier_name": carrier,
            "tracking_number": tracking,
            "notes": notes,
        }

        paypal_response = await self.client.provide_evidence(dispute_id, evidence_payload)

        # 5. Record immutable cryptographic audit entry (DSP022)
        await self.audit.log_action(
            dispute_id=dispute_id,
            action="EVIDENCE_SUBMITTED",
            actor="system",
            details={
                "evidence_type": evidence_payload["evidence_type"],
                "carrier_name": evidence_payload["carrier_name"],
                "tracking_number": evidence_payload["tracking_number"],
                "urgency_tier": urgency_tier,
                "hours_until_due": hours_until_due,
                "paypal_status": paypal_response.get("status", "SUCCESS"),
            },
            previous_state=InternalState.INGESTED.value,
            new_state=InternalState.DISPATCHED.value,
        )

        # 6. Parse dispute attributes and persist updated record in database
        amt_data = webhook_resource.get("dispute_amount", {})
        currency = str(amt_data.get("currency") or amt_data.get("currency_code") or "USD")
        value = float(amt_data.get("value", 0.0))
        money = Money(currency=currency, value=value)

        raw_reason = webhook_resource.get(
            "reason", DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED.value
        )
        try:
            reason = DisputeReason(str(raw_reason))
        except ValueError:
            reason = DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED

        raw_status = webhook_resource.get("status", DisputeStatus.WAITING_FOR_SELLER_RESPONSE.value)
        try:
            status = DisputeStatus(str(raw_status))
        except ValueError:
            status = DisputeStatus.WAITING_FOR_SELLER_RESPONSE

        raw_stage = webhook_resource.get(
            "dispute_life_cycle_stage", DisputeLifeCycleStage.CHARGEBACK.value
        )
        try:
            stage = DisputeLifeCycleStage(str(raw_stage))
        except ValueError:
            stage = DisputeLifeCycleStage.CHARGEBACK

        allowed_links = [
            str(link.get("rel"))
            for link in links
            if isinstance(link, dict) and "rel" in link
        ]

        dispute_record = DisputeRecord(
            dispute_id=dispute_id,
            reason=reason,
            status=status,
            dispute_life_cycle_stage=stage,
            dispute_amount=money,
            seller_response_due_date=due_date_iso or "",
            hours_until_due=hours_until_due,
            allowed_links=allowed_links,
            internal_state=InternalState.DISPATCHED,
            recommended_action=RecommendedAction.CONTEST,
            win_probability=0.85,
            expected_recovery=money.value,
        )

        await self.repo.save_dispute(dispute_record)
        return dispute_record
