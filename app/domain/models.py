"""Core domain data models and enumerations for DisputeSentry AI."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class DisputeReason(str, Enum):
    """Reason code reported for a dispute."""

    MERCHANDISE_OR_SERVICE_NOT_RECEIVED = "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
    MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED"
    UNAUTHORISED = "UNAUTHORISED"
    CREDIT_NOT_PROCESSED = "CREDIT_NOT_PROCESSED"
    OTHER = "OTHER"


class DisputeStatus(str, Enum):
    """External status reported by PayPal."""

    OPEN = "OPEN"
    WAITING_FOR_SELLER_RESPONSE = "WAITING_FOR_SELLER_RESPONSE"
    WAITING_FOR_BUYER_RESPONSE = "WAITING_FOR_BUYER_RESPONSE"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"


class DisputeLifeCycleStage(str, Enum):
    """Current lifecycle stage of the dispute."""

    INQUIRY = "INQUIRY"
    CHARGEBACK = "CHARGEBACK"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    ARBITRATION = "ARBITRATION"


class InternalState(str, Enum):
    """Internal state machine status within DisputeSentry AI."""

    INGESTED = "INGESTED"
    EVALUATING = "EVALUATING"
    AUTO_READY = "AUTO_READY"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"
    ERROR_PAUSED = "ERROR_PAUSED"


class RecommendedAction(str, Enum):
    """Decision engine recommendation for dispute resolution."""

    CONTEST = "CONTEST"
    CONCEDE = "CONCEDE"
    INQUIRY_OFFER = "INQUIRY_OFFER"
    SEND_MESSAGE = "SEND_MESSAGE"
    ESCALATE = "ESCALATE"


class ProtectionEligibility(str, Enum):
    """PayPal Seller Protection eligibility tier."""

    ELIGIBLE = "ELIGIBLE"
    PARTIALLY_ELIGIBLE = "PARTIALLY_ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"


class Money(BaseModel):
    """Monetary amount with ISO 4217 currency code."""

    model_config = ConfigDict(frozen=True)

    currency: str = Field(default="USD", min_length=3, max_length=3)
    value: float = Field(default=0.0, ge=0.0)

    @field_serializer("value")
    def serialize_value(self, v: float) -> float:
        """Format value with 2 decimal places precision."""
        return round(v, 2)


class MerchantOrderRecord(BaseModel):
    """Internal merchant fulfillment record retrieved from local database."""

    model_config = ConfigDict(extra="ignore")

    order_id: str = Field(min_length=1)
    transaction_id: str = Field(min_length=1)
    buyer_email: str = Field(min_length=1)
    shipping_address: dict[str, str]
    carrier: str = Field(min_length=1)
    tracking_number: str = Field(min_length=1)
    delivery_status: str = Field(min_length=1)
    shipped_date: str = Field(min_length=1)
    delivery_date: str | None = None
    refund_history: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("shipping_address")
    @classmethod
    def validate_shipping_address(cls, v: dict[str, str]) -> dict[str, str]:
        """Ensure shipping address contains required address components."""
        if "country_code" not in v or "postal_code" not in v:
            raise ValueError(
                "shipping_address must contain at least 'country_code' and 'postal_code'"
            )
        return v


class DisputeRecord(BaseModel):
    """Core domain model representing a PayPal dispute and internal processing state."""

    model_config = ConfigDict(extra="ignore")

    dispute_id: str = Field(min_length=1)
    create_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    reason: DisputeReason
    status: DisputeStatus
    dispute_life_cycle_stage: DisputeLifeCycleStage
    dispute_amount: Money
    seller_response_due_date: str
    hours_until_due: float = Field(default=0.0)
    allowed_links: list[str] = Field(default_factory=list)
    internal_state: InternalState = Field(default=InternalState.INGESTED)
    recommended_action: RecommendedAction | None = None
    win_probability: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_recovery: float = Field(default=0.0, ge=0.0)
    assigned_operator: str | None = None
    customer_notes: str = Field(default="")

    @model_validator(mode="after")
    def enforce_invariants(self) -> DisputeRecord:
        """Enforce business rules and human gate invariants."""
        # Invariant: Never auto-execute concessions on disputes >= $100 without human approval
        auto_states = (
            InternalState.AUTO_READY,
            InternalState.INGESTED,
            InternalState.EVALUATING,
        )
        if (
            self.dispute_amount.value >= 100.0
            and self.recommended_action == RecommendedAction.CONCEDE
            and self.internal_state in auto_states
        ):
            self.internal_state = InternalState.PENDING_APPROVAL
        return self


class AuditTrailEntry(BaseModel):
    """Append-only cryptographic audit record for dispute state transitions."""

    model_config = ConfigDict(frozen=True)

    entry_id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    dispute_id: str = Field(min_length=1)
    action: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str = Field(default="0" * 64, min_length=64, max_length=64)
    entry_hash: str = Field(default="", max_length=64)
    previous_state: str | None = None
    new_state: str | None = None


class MerchantEvidencePackage(BaseModel):
    """Structured evidence package returned when matching disputes to merchant orders."""

    model_config = ConfigDict(extra="ignore")

    order: MerchantOrderRecord | None = None
    carrier: str | None = None
    shipment_status: str | None = None
    tracking_number: str | None = None
    customer_notes: list[str] = Field(default_factory=list)
    record_found: bool = True
    status: str = Field(default="RECORD_FOUND")
