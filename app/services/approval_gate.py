"""Human-in-the-Loop Approval Gate and concession executor (DSP013, DSP015)."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.clients.paypal_client import PayPalAPIError, PayPalDisputesClient
from app.domain.exceptions import DisputeSentryError
from app.domain.models import (
    DisputeRecord,
    DisputeStatus,
    InternalState,
    RecommendedAction,
)
from app.services.audit_service import AuditService
from app.storage.repository import MerchantRepository

logger = logging.getLogger(__name__)


class DisputeNotFoundError(DisputeSentryError):
    """Raised when an operation targets a non-existent dispute record."""


class InvalidStateTransitionError(DisputeSentryError):
    """Raised when an unlawful or invalid state machine transition is attempted."""


class DisputeAlreadyClosedError(DisputeSentryError):
    """Raised when an action is attempted on an already closed/resolved dispute (DSP015)."""

    def __init__(
        self,
        message: str = "Dispute is already closed",
        error_code: str = "DISPUTE_ALREADY_CLOSED",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class GateEvaluationResult(BaseModel):
    """Result of evaluating dispute against human approval policy criteria (DSP013)."""

    model_config = ConfigDict(frozen=True)

    requires_human_approval: bool
    decision_state: str
    trigger_reason: str | None = None


def evaluate_gate_criteria(
    amount: float,
    confidence: float,
    recommended_action: str | RecommendedAction | None = None,
    approval_threshold_usd: float = 100.0,
    min_confidence: float = 0.65,
) -> GateEvaluationResult:
    """Evaluate financial gate and confidence criteria for human review gating (DSP013).

    Args:
        amount: Dispute monetary amount in USD.
        confidence: Evaluated win probability / model confidence score.
        recommended_action: Recommended dispute resolution action.
        approval_threshold_usd: Dollar threshold above which review is compulsory.
        min_confidence: Minimum confidence score to allow automated execution.

    Returns:
        GateEvaluationResult with gating status, decision_state, and trigger reason.
    """
    action_str = (
        recommended_action.value
        if isinstance(recommended_action, RecommendedAction)
        else str(recommended_action) if recommended_action is not None else None
    )

    # 1. High value financial threshold ($100.00 default)
    if amount >= approval_threshold_usd:
        return GateEvaluationResult(
            requires_human_approval=True,
            decision_state=InternalState.PENDING_APPROVAL.value,
            trigger_reason="AMOUNT_EXCEEDS_THRESHOLD",
        )

    # 2. Concession actions always require human sign-off (DSP015)
    if action_str == RecommendedAction.CONCEDE.value:
        return GateEvaluationResult(
            requires_human_approval=True,
            decision_state=InternalState.PENDING_APPROVAL.value,
            trigger_reason="CONCESSION_ACTION_REQUIRES_APPROVAL",
        )

    # 3. Low confidence decisions require human review
    if confidence <= min_confidence:
        return GateEvaluationResult(
            requires_human_approval=True,
            decision_state=InternalState.PENDING_APPROVAL.value,
            trigger_reason="CONFIDENCE_BELOW_THRESHOLD",
        )

    # 4. Low value, high confidence contest action is auto-ready
    return GateEvaluationResult(
        requires_human_approval=False,
        decision_state="AUTO_EXECUTING",
        trigger_reason=None,
    )


class ApprovalGateService:
    """Manages human-in-the-loop review state machine and concession executions (DSP013, DSP015)."""

    def __init__(
        self,
        repo: MerchantRepository,
        client: PayPalDisputesClient,
        audit: AuditService,
        approval_threshold_usd: float = 100.0,
        min_confidence: float = 0.65,
    ) -> None:
        self.repo = repo
        self.client = client
        self.audit = audit
        self.approval_threshold_usd = approval_threshold_usd
        self.min_confidence = min_confidence

    async def evaluate_gate(self, dispute: DisputeRecord) -> InternalState:
        """Evaluate dispute parameters and transition to AUTO_READY or PENDING_APPROVAL.

        Args:
            dispute: DisputeRecord to evaluate.

        Returns:
            Resolved InternalState (PENDING_APPROVAL or AUTO_READY).
        """
        eval_result = evaluate_gate_criteria(
            amount=dispute.dispute_amount.value,
            confidence=dispute.win_probability,
            recommended_action=dispute.recommended_action,
            approval_threshold_usd=self.approval_threshold_usd,
            min_confidence=self.min_confidence,
        )

        previous_state = dispute.internal_state
        new_state = (
            InternalState.PENDING_APPROVAL
            if eval_result.requires_human_approval
            else InternalState.AUTO_READY
        )

        dispute.internal_state = new_state
        if self.repo.db is not None:
            await self.repo.save_dispute(dispute)

        if self.audit.db is not None:
            await self.audit.log_action(
                dispute_id=dispute.dispute_id,
                action=f"EVALUATE_GATE_{new_state.value}",
                actor="system:approval_gate",
                details={
                    "amount": dispute.dispute_amount.value,
                    "win_probability": dispute.win_probability,
                    "recommended_action": (
                        dispute.recommended_action.value
                        if dispute.recommended_action
                        else None
                    ),
                    "trigger_reason": eval_result.trigger_reason,
                },
                previous_state=previous_state.value,
                new_state=new_state.value,
            )

        return new_state

    async def approve_dispute(
        self,
        dispute_id: str,
        operator_id: str,
        notes: str = "",
    ) -> DisputeRecord:
        """Approve a locked dispute, transitioning PENDING_APPROVAL -> APPROVED -> DISPATCHED.

        Args:
            dispute_id: Identifier of dispute to approve.
            operator_id: Identifier of approving human operator.
            notes: Optional operator approval review notes.

        Returns:
            Updated DisputeRecord in DISPATCHED state.

        Raises:
            DisputeNotFoundError: Dispute ID does not exist in repository.
            InvalidStateTransitionError: Dispute is not currently in PENDING_APPROVAL.
        """
        dispute = await self.repo.get_dispute(dispute_id)
        if dispute is None:
            raise DisputeNotFoundError(f"Dispute not found: {dispute_id}")

        if dispute.internal_state != InternalState.PENDING_APPROVAL:
            raise InvalidStateTransitionError(
                f"Cannot approve dispute in state {dispute.internal_state.value}; "
                "must be PENDING_APPROVAL"
            )

        # Atomic SQLite update ensuring no race condition with deadline fail-safe
        async with self.repo.db.execute(
            """
            UPDATE disputes
            SET internal_state = ?, assigned_operator = ?
            WHERE dispute_id = ? AND internal_state = ?
            """,
            (
                InternalState.APPROVED.value,
                operator_id,
                dispute_id,
                InternalState.PENDING_APPROVAL.value,
            ),
        ) as cursor:
            if cursor.rowcount == 0:
                # Concurrent update occurred
                current = await self.repo.get_dispute(dispute_id)
                curr_state = current.internal_state.value if current else "UNKNOWN"
                raise InvalidStateTransitionError(
                    f"Dispute state changed concurrently to {curr_state}"
                )
        await self.repo.db.commit()

        dispute.assigned_operator = operator_id
        dispute.internal_state = InternalState.APPROVED

        await self.audit.log_action(
            dispute_id=dispute_id,
            action="OPERATOR_APPROVE",
            actor=operator_id,
            details={"notes": notes},
            previous_state=InternalState.PENDING_APPROVAL.value,
            new_state=InternalState.APPROVED.value,
        )

        # Execute approved mutation against PayPal API
        if dispute.recommended_action == RecommendedAction.CONCEDE:
            await self.accept_claim(
                dispute_id=dispute_id,
                note=notes or "Concession approved by human operator",
                current_status=dispute.status.value,
            )

        # Transition APPROVED -> DISPATCHED
        dispute.internal_state = InternalState.DISPATCHED
        await self.repo.save_dispute(dispute)

        await self.audit.log_action(
            dispute_id=dispute_id,
            action="DISPATCH_MUTATION",
            actor=operator_id,
            details={
                "action": (
                    dispute.recommended_action.value
                    if dispute.recommended_action
                    else "CONTEST"
                )
            },
            previous_state=InternalState.APPROVED.value,
            new_state=InternalState.DISPATCHED.value,
        )

        return dispute

    async def reject_dispute(
        self,
        dispute_id: str,
        operator_id: str,
        reason: str = "",
    ) -> DisputeRecord:
        """Reject recommended action on locked dispute, transitioning to REJECTED.

        Args:
            dispute_id: Identifier of dispute to reject.
            operator_id: Identifier of rejecting human operator.
            reason: Optional explanation for rejection.

        Returns:
            Updated DisputeRecord in REJECTED state.

        Raises:
            DisputeNotFoundError: Dispute ID does not exist in repository.
            InvalidStateTransitionError: Dispute is not currently in PENDING_APPROVAL.
        """
        dispute = await self.repo.get_dispute(dispute_id)
        if dispute is None:
            raise DisputeNotFoundError(f"Dispute not found: {dispute_id}")

        if dispute.internal_state != InternalState.PENDING_APPROVAL:
            raise InvalidStateTransitionError(
                f"Cannot reject dispute in state {dispute.internal_state.value}; "
                "must be PENDING_APPROVAL"
            )

        # Atomic SQLite update
        async with self.repo.db.execute(
            """
            UPDATE disputes
            SET internal_state = ?, assigned_operator = ?
            WHERE dispute_id = ? AND internal_state = ?
            """,
            (
                InternalState.REJECTED.value,
                operator_id,
                dispute_id,
                InternalState.PENDING_APPROVAL.value,
            ),
        ) as cursor:
            if cursor.rowcount == 0:
                current = await self.repo.get_dispute(dispute_id)
                curr_state = current.internal_state.value if current else "UNKNOWN"
                raise InvalidStateTransitionError(
                    f"Dispute state changed concurrently to {curr_state}"
                )
        await self.repo.db.commit()

        dispute.assigned_operator = operator_id
        dispute.internal_state = InternalState.REJECTED

        await self.audit.log_action(
            dispute_id=dispute_id,
            action="OPERATOR_REJECT",
            actor=operator_id,
            details={"reason": reason},
            previous_state=InternalState.PENDING_APPROVAL.value,
            new_state=InternalState.REJECTED.value,
        )

        return dispute

    async def accept_claim(
        self,
        dispute_id: str,
        note: str = "Accepting claim.",
        current_status: str | None = None,
    ) -> dict[str, Any]:
        """Execute accept-claim concession call to PayPal Disputes API v1 (DSP015).

        Args:
            dispute_id: Identifier of dispute.
            note: Merchant concession note to buyer/PayPal.
            current_status: Optional dispute status string to check if already closed.

        Returns:
            Dictionary payload confirming API submission.

        Raises:
            DisputeAlreadyClosedError: If dispute is already in RESOLVED status.
            PayPalAPIError: If PayPal API returns HTTP 4xx or 5xx.
        """
        if current_status and current_status.upper() in (
            "RESOLVED",
            DisputeStatus.RESOLVED.value,
        ):
            raise DisputeAlreadyClosedError(
                "Cannot accept claim on a dispute that is already in RESOLVED state",
                error_code="DISPUTE_ALREADY_CLOSED",
            )

        if self.repo.db is not None:
            existing = await self.repo.get_dispute(dispute_id)
            if existing is not None and existing.status == DisputeStatus.RESOLVED:
                raise DisputeAlreadyClosedError(
                    "Cannot accept claim on a dispute that is already in RESOLVED state",
                    error_code="DISPUTE_ALREADY_CLOSED",
                )

        url = f"{self.client.base_url}/v1/customer/disputes/{dispute_id}/accept-claim"
        token = await self.client.get_access_token()
        http_client = await self.client._get_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        payload = {"note": note}

        try:
            response = await http_client.post(url, headers=headers, json=payload)
        except Exception as exc:
            raise PayPalAPIError(
                f"Network error executing accept-claim on {dispute_id}: {exc}"
            ) from exc

        # Automatic 401 retry with token refresh
        if response.status_code == 401:
            token = await self.client.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = await http_client.post(url, headers=headers, json=payload)
            except Exception as exc:
                raise PayPalAPIError(
                    f"Network error on retry executing accept-claim on {dispute_id}: {exc}"
                ) from exc

        if response.status_code not in (200, 201, 204):
            err_msg = (
                f"POST accept-claim for {dispute_id} failed "
                f"({response.status_code}): {response.text}"
            )
            raise PayPalAPIError(
                err_msg,
                status_code=response.status_code,
                response_body=response.text,
            )

        if self.audit.db is not None:
            await self.audit.log_action(
                dispute_id=dispute_id,
                action="ACCEPT_CLAIM_CONCESSION",
                actor="system",
                details={"note": note, "paypal_status": response.status_code},
                previous_state=InternalState.APPROVED.value,
                new_state="CLAIM_ACCEPTED",
            )

        return {
            "status": "CLAIM_ACCEPTED",
            "api_endpoint": f"POST /v1/customer/disputes/{dispute_id}/accept-claim",
            "expected_paypal_status": 200,
            "new_state": "CLAIM_ACCEPTED",
        }


# Dynamic binding to ensure client.accept_claim works seamlessly if called directly
async def _client_accept_claim(
    self: PayPalDisputesClient,
    dispute_id: str,
    note: str = "Accepting claim.",
    status: str | None = None,
) -> dict[str, Any]:
    """Helper method attached to PayPalDisputesClient for executing accept-claim."""
    if status and status.upper() in ("RESOLVED", DisputeStatus.RESOLVED.value):
        raise DisputeAlreadyClosedError(
            "Cannot accept claim on a dispute that is already in RESOLVED state",
            error_code="DISPUTE_ALREADY_CLOSED",
        )

    url = f"{self.base_url}/v1/customer/disputes/{dispute_id}/accept-claim"
    token = await self.get_access_token()
    http_client = await self._get_client()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    response = await http_client.post(url, headers=headers, json={"note": note})
    if response.status_code not in (200, 201, 204):
        raise PayPalAPIError(
            f"POST accept-claim failed ({response.status_code}): {response.text}",
            status_code=response.status_code,
            response_body=response.text,
        )
    return {
        "status": "CLAIM_ACCEPTED",
        "api_endpoint": f"POST /v1/customer/disputes/{dispute_id}/accept-claim",
        "expected_paypal_status": 200,
        "new_state": "CLAIM_ACCEPTED",
    }


if not hasattr(PayPalDisputesClient, "accept_claim"):
    PayPalDisputesClient.accept_claim = _client_accept_claim  # type: ignore[attr-defined]
