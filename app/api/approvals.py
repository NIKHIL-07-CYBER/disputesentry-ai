"""FastAPI routes for operator dispute approval, rejection, and oversight (DSP013)."""

from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.clients.paypal_client import PayPalDisputesClient
from app.config import AppConfig, get_config
from app.services.approval_gate import (
    ApprovalGateService,
    DisputeAlreadyClosedError,
    DisputeNotFoundError,
    InvalidStateTransitionError,
)
from app.services.audit_service import AuditService
from app.storage.database import open_database
from app.storage.repository import MerchantRepository

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Approvals"])


class ApproveDisputeRequest(BaseModel):
    """Payload submitted when operator approves a pending dispute."""

    model_config = ConfigDict(extra="ignore")

    operator_id: str = Field(min_length=1, description="Identifier of approving operator")
    notes: str = Field(default="", description="Operator rationale or representment instructions")


class RejectDisputeRequest(BaseModel):
    """Payload submitted when operator rejects recommended action on a dispute."""

    model_config = ConfigDict(extra="ignore")

    operator_id: str = Field(min_length=1, description="Identifier of rejecting operator")
    reason: str = Field(default="", description="Explanation for decision rejection")


class ApproveDisputeResponse(BaseModel):
    """Response returned upon successful dispute approval."""

    dispute_id: str
    status: str
    internal_state: str
    assigned_operator: str
    executed_action: str
    message: str = "Dispute approved and dispatched"


class RejectDisputeResponse(BaseModel):
    """Response returned upon successful dispute rejection."""

    dispute_id: str
    status: str
    internal_state: str
    assigned_operator: str
    reason: str
    message: str = "Dispute rejected"


async def get_approval_gate_service(request: Request) -> ApprovalGateService:
    """Dependency resolver for ApprovalGateService instance."""
    app_state = getattr(request.app, "state", None)
    if app_state and hasattr(app_state, "approval_gate_service"):
        svc = app_state.approval_gate_service
        if isinstance(svc, ApprovalGateService):
            return svc

    config_obj = getattr(app_state, "config", None) if app_state else None
    config: AppConfig = config_obj if isinstance(config_obj, AppConfig) else get_config()

    client = PayPalDisputesClient(
        client_id=config.paypal_client_id,
        client_secret=config.paypal_client_secret,
        base_url=config.paypal_api_base,
    )
    db_path = config.database_url.removeprefix("sqlite+aiosqlite:///")
    async with open_database(db_path) as db:
        repo = MerchantRepository(db)
        audit = AuditService(db)
        return ApprovalGateService(
            repo=repo,
            client=client,
            audit=audit,
            approval_threshold_usd=config.high_value_threshold_usd,
            min_confidence=0.65,
        )


@router.post(
    "/api/disputes/{dispute_id}/approve",
    response_model=ApproveDisputeResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/api/v1/disputes/{dispute_id}/approve",
    response_model=ApproveDisputeResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def approve_dispute(
    dispute_id: str,
    payload: ApproveDisputeRequest,
    service: Annotated[ApprovalGateService, Depends(get_approval_gate_service)],
) -> ApproveDisputeResponse:
    """Approve a pending dispute for automated submission to PayPal."""
    try:
        updated = await service.approve_dispute(
            dispute_id=dispute_id,
            operator_id=payload.operator_id,
            notes=payload.notes,
        )
    except DisputeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except (InvalidStateTransitionError, DisputeAlreadyClosedError) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    action_name = (
        updated.recommended_action.value
        if updated.recommended_action is not None
        else "CONTEST"
    )

    return ApproveDisputeResponse(
        dispute_id=updated.dispute_id,
        status=updated.status.value,
        internal_state=updated.internal_state.value,
        assigned_operator=updated.assigned_operator or payload.operator_id,
        executed_action=action_name,
    )


@router.post(
    "/api/disputes/{dispute_id}/reject",
    response_model=RejectDisputeResponse,
    status_code=status.HTTP_200_OK,
)
@router.post(
    "/api/v1/disputes/{dispute_id}/reject",
    response_model=RejectDisputeResponse,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def reject_dispute(
    dispute_id: str,
    payload: RejectDisputeRequest,
    service: Annotated[ApprovalGateService, Depends(get_approval_gate_service)],
) -> RejectDisputeResponse:
    """Reject recommended action on a pending dispute, marking it REJECTED."""
    try:
        updated = await service.reject_dispute(
            dispute_id=dispute_id,
            operator_id=payload.operator_id,
            reason=payload.reason,
        )
    except DisputeNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except InvalidStateTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    return RejectDisputeResponse(
        dispute_id=updated.dispute_id,
        status=updated.status.value,
        internal_state=updated.internal_state.value,
        assigned_operator=updated.assigned_operator or payload.operator_id,
        reason=payload.reason,
    )
