"""PayPal Seller Protection deterministic rule engine for DisputeSentry AI.

Evaluates dispute claims against merchant fulfillment records and PayPal Seller Protection
policies across:
- Item Not Received (INR - DSP007): Online carrier tracking & delivery postal code verification.
- Unauthorised Payment (DSP008): Timely dispatch prior to unauthorized notification.
- Significantly Not As Described (SNAD - DSP009): Prior refund and return policy compliance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, computed_field

from app.domain.models import (
    DisputeLifeCycleStage,
    DisputeReason,
    DisputeRecord,
    DisputeStatus,
    MerchantOrderRecord,
    Money,
    ProtectionEligibility,
    RecommendedAction,
)


def normalize_postal_code(code: str | None) -> str:
    """Normalize postal codes by removing whitespace, hyphens, and converting to uppercase."""
    if not code:
        return ""
    return "".join(c for c in code if c.isalnum()).upper()


def postal_codes_match(code1: str | None, code2: str | None) -> bool:
    """Check if two postal codes match, handling ZIP+4, spaces, and international formatting.

    Returns True if:
    - Normalized codes are identical.
    - Both codes have >= 5 alphanumeric characters and share the first 5 characters (ZIP+4).
    """
    c1 = normalize_postal_code(code1)
    c2 = normalize_postal_code(code2)
    if not c1 or not c2:
        return False
    if c1 == c2:
        return True
    min_len = min(len(c1), len(c2))
    if min_len >= 5 and c1[:5] == c2[:5]:
        return True
    return False


def parse_iso_datetime(dt_val: str | datetime | None) -> datetime | None:
    """Parse an ISO 8601 timestamp string or datetime into a UTC-aware datetime."""
    if not dt_val:
        return None
    if isinstance(dt_val, datetime):
        return dt_val if dt_val.tzinfo is not None else dt_val.replace(tzinfo=UTC)
    try:
        cleaned = dt_val.replace("Z", "+00:00")
        dt = datetime.fromisoformat(cleaned)
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)
    except Exception:
        return None


class ProtectionEvaluationResult(BaseModel):
    """Structured evaluation output containing Seller Protection tier and win probability."""

    model_config = ConfigDict(frozen=True)

    eligibility: ProtectionEligibility
    win_probability: float = Field(ge=0.0, le=1.0)
    evidence_type: str = Field(default="NONE")
    recommended_action: RecommendedAction = RecommendedAction.CONTEST
    reasons: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[prop-decorator]
    @property
    def seller_protection_eligible(self) -> bool:
        """Indicate whether the dispute qualifies for full PayPal Seller Protection."""
        return self.eligibility == ProtectionEligibility.ELIGIBLE


class SellerProtectionEngine:
    """Deterministic policy rule engine for PayPal Seller Protection eligibility."""

    @staticmethod
    def evaluate(
        dispute: DisputeRecord,
        order: MerchantOrderRecord | None = None,
        *,
        carrier_delivery_postal_code: str | None = None,
        shipping_address_matches_paypal: bool | None = None,
        customer_comms_present: bool = False,
        merchant_return_policy_signed: bool = False,
    ) -> ProtectionEvaluationResult:
        """Evaluate Seller Protection eligibility and win probability for a dispute."""
        if order is None:
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=["No merchant fulfillment record found for dispute"],
            )

        if dispute.reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED:
            return SellerProtectionEngine._evaluate_inr(
                dispute=dispute,
                order=order,
                carrier_delivery_postal_code=carrier_delivery_postal_code,
            )

        if dispute.reason == DisputeReason.UNAUTHORISED:
            return SellerProtectionEngine._evaluate_unauthorised(
                dispute=dispute,
                order=order,
                shipping_address_matches_paypal=shipping_address_matches_paypal,
            )

        if dispute.reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED:
            return SellerProtectionEngine._evaluate_snad(
                dispute=dispute,
                order=order,
                customer_comms_present=customer_comms_present,
                merchant_return_policy_signed=merchant_return_policy_signed,
            )

        return ProtectionEvaluationResult(
            eligibility=ProtectionEligibility.INELIGIBLE,
            win_probability=0.30,
            evidence_type="NONE",
            recommended_action=RecommendedAction.CONCEDE,
            reasons=[f"Unsupported or unhandled dispute reason: {dispute.reason.value}"],
        )

    @staticmethod
    def _evaluate_inr(
        dispute: DisputeRecord,
        order: MerchantOrderRecord,
        carrier_delivery_postal_code: str | None,
    ) -> ProtectionEvaluationResult:
        """Evaluate Item Not Received claims (DSP007)."""
        expected_zip = order.shipping_address.get("postal_code")
        actual_zip = (
            carrier_delivery_postal_code
            or order.shipping_address.get("delivery_postal_code")
            or order.shipping_address.get("delivery_zip")
        )

        if actual_zip is not None and not postal_codes_match(expected_zip, actual_zip):
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=[
                    f"Delivery postal code '{actual_zip}' does not match "
                    f"order shipping address postal code '{expected_zip}'"
                ],
            )

        if order.delivery_date:
            delivery_dt = parse_iso_datetime(order.delivery_date)
            dispute_dt = parse_iso_datetime(dispute.create_time)
            if delivery_dt and dispute_dt and delivery_dt > dispute_dt:
                return ProtectionEvaluationResult(
                    eligibility=ProtectionEligibility.INELIGIBLE,
                    win_probability=0.05,
                    evidence_type="NONE",
                    recommended_action=RecommendedAction.CONCEDE,
                    reasons=["Delivery occurred after dispute creation time"],
                )

        norm_status = order.delivery_status.strip().upper()
        if norm_status == "DELIVERED":
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.ELIGIBLE,
                win_probability=0.92,
                evidence_type="PROOF_OF_FULFILLMENT",
                recommended_action=RecommendedAction.CONTEST,
                reasons=[
                    f"Carrier '{order.carrier}' confirmed delivery to recipient "
                    f"postal code '{expected_zip}' prior to dispute creation"
                ],
            )

        if norm_status in ("IN_TRANSIT", "OUT_FOR_DELIVERY"):
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.PARTIALLY_ELIGIBLE,
                win_probability=0.60,
                evidence_type="PROOF_OF_FULFILLMENT",
                recommended_action=RecommendedAction.CONTEST,
                reasons=[
                    f"Shipment is currently '{norm_status}' with carrier '{order.carrier}' "
                    f"tracking '{order.tracking_number}'"
                ],
            )

        return ProtectionEvaluationResult(
            eligibility=ProtectionEligibility.INELIGIBLE,
            win_probability=0.05,
            evidence_type="NONE",
            recommended_action=RecommendedAction.CONCEDE,
            reasons=[
                f"Carrier tracking status '{order.delivery_status}' does not confirm delivery"
            ],
        )

    @staticmethod
    def _evaluate_unauthorised(
        dispute: DisputeRecord,
        order: MerchantOrderRecord,
        shipping_address_matches_paypal: bool | None,
    ) -> ProtectionEvaluationResult:
        """Evaluate Unauthorised transaction claims (DSP008)."""
        if not order.shipped_date or not order.shipped_date.strip():
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=["Missing proof of shipment date for unauthorized transaction"],
            )

        shipped_dt = parse_iso_datetime(order.shipped_date)
        dispute_dt = parse_iso_datetime(dispute.create_time)

        if shipped_dt is None:
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=["Proof of shipment timestamp could not be parsed"],
            )

        if dispute_dt is not None and shipped_dt >= dispute_dt:
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=[
                    f"Shipment dispatch ({order.shipped_date}) occurred after "
                    f"PayPal dispute notification ({dispute.create_time})"
                ],
            )

        addr_matches = shipping_address_matches_paypal
        if addr_matches is None:
            raw_match = order.shipping_address.get("matches_paypal", True)
            if isinstance(raw_match, str):
                addr_matches = raw_match.lower() in ("true", "1")
            else:
                addr_matches = bool(raw_match)

        if not addr_matches:
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.INELIGIBLE,
                win_probability=0.05,
                evidence_type="NONE",
                recommended_action=RecommendedAction.CONCEDE,
                reasons=[
                    "Shipping address does not match destination on PayPal transaction details"
                ],
            )

        return ProtectionEvaluationResult(
            eligibility=ProtectionEligibility.ELIGIBLE,
            win_probability=0.88,
            evidence_type="PROOF_OF_FULFILLMENT",
            recommended_action=RecommendedAction.CONTEST,
            reasons=[
                f"Proof of shipment verified with dispatch timestamp {order.shipped_date} "
                f"prior to dispute notification {dispute.create_time}"
            ],
        )

    @staticmethod
    def _evaluate_snad(
        dispute: DisputeRecord,
        order: MerchantOrderRecord,
        customer_comms_present: bool,
        merchant_return_policy_signed: bool,
    ) -> ProtectionEvaluationResult:
        """Evaluate Significantly Not As Described claims (DSP009)."""
        if order.refund_history:
            for ref in order.refund_history:
                ref_id = ref.get("refund_id") or ref.get("refund_transaction_id") or ref.get("id")
                return ProtectionEvaluationResult(
                    eligibility=ProtectionEligibility.ELIGIBLE,
                    win_probability=0.95,
                    evidence_type="PROOF_OF_REFUND",
                    recommended_action=RecommendedAction.CONTEST,
                    reasons=[
                        f"Prior refund issued under transaction {ref_id or 'REFUND'}"
                    ],
                )

        policy_signed = merchant_return_policy_signed
        if not policy_signed:
            raw_pol = order.shipping_address.get("merchant_return_policy_signed")
            if isinstance(raw_pol, bool):
                policy_signed = raw_pol
            elif isinstance(raw_pol, str):
                policy_signed = raw_pol.lower() in ("true", "1")

        if policy_signed:
            return ProtectionEvaluationResult(
                eligibility=ProtectionEligibility.PARTIALLY_ELIGIBLE,
                win_probability=0.60,
                evidence_type="MERCHANT_RETURN_POLICY",
                recommended_action=RecommendedAction.CONTEST,
                reasons=["Merchant return policy agreed and accepted at checkout"],
            )

        return ProtectionEvaluationResult(
            eligibility=ProtectionEligibility.INELIGIBLE,
            win_probability=0.20,
            evidence_type="NONE",
            recommended_action=RecommendedAction.CONCEDE,
            reasons=["No prior refund or return agreement found for SNAD claim"],
        )

    @staticmethod
    def evaluate_fixture(data: dict[str, Any]) -> ProtectionEvaluationResult:
        """Parse raw catalog fixture JSON and execute evaluation."""
        reason_str = str(data.get("reason", "OTHER"))
        reason = DisputeReason(reason_str)
        create_time = str(data.get("dispute_create_time", "2026-10-28T10:00:00Z"))

        amt_data = data.get("dispute_amount", {})
        if isinstance(amt_data, dict) and "value" in amt_data:
            val = float(amt_data["value"])
            curr = str(amt_data.get("currency", "USD"))
        else:
            val = 75.0
            curr = "USD"

        dispute = DisputeRecord(
            dispute_id="DISPUTE-FIXTURE",
            create_time=create_time,
            reason=reason,
            status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
            dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
            dispute_amount=Money(currency=curr, value=val),
            seller_response_due_date="2026-11-10T00:00:00Z",
        )

        evidence: dict[str, Any] = data.get("evidence", {})

        if reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED:
            shipping_zip = str(evidence.get("transaction_shipping_zip", "94107"))
            delivery_zip = evidence.get("delivery_zip")
            carrier = str(evidence.get("carrier", "USPS"))
            tracking_number = str(evidence.get("tracking_number", "9400111899223197428490"))
            tracking_status = str(evidence.get("tracking_status", "DELIVERED"))
            delivery_timestamp = evidence.get("delivery_timestamp")

            order = MerchantOrderRecord(
                order_id="ORD-FIXTURE",
                transaction_id="TXN-FIXTURE",
                buyer_email="buyer@example.com",
                shipping_address={"country_code": "US", "postal_code": shipping_zip},
                carrier=carrier,
                tracking_number=tracking_number,
                delivery_status=tracking_status,
                shipped_date="2026-10-20T10:00:00Z",
                delivery_date=str(delivery_timestamp) if delivery_timestamp else None,
            )
            return SellerProtectionEngine.evaluate(
                dispute,
                order,
                carrier_delivery_postal_code=str(delivery_zip) if delivery_zip else None,
            )

        if reason == DisputeReason.UNAUTHORISED:
            carrier = str(evidence.get("carrier", "FedEx"))
            tracking_number = str(evidence.get("tracking_number", "794644792180"))
            shipment_timestamp = str(evidence.get("shipment_timestamp", ""))
            addr_matches = bool(evidence.get("shipping_address_matches_paypal", True))

            order = MerchantOrderRecord(
                order_id="ORD-FIXTURE",
                transaction_id="TXN-FIXTURE",
                buyer_email="buyer@example.com",
                shipping_address={"country_code": "US", "postal_code": "94107"},
                carrier=carrier,
                tracking_number=tracking_number,
                delivery_status="DELIVERED",
                shipped_date=shipment_timestamp,
            )
            return SellerProtectionEngine.evaluate(
                dispute,
                order,
                shipping_address_matches_paypal=addr_matches,
            )

        if reason == DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED:
            refund_issued = bool(evidence.get("prior_refund_issued", False))
            refund_history: list[dict[str, Any]] = []
            if refund_issued:
                refund_history.append(
                    {
                        "refund_id": evidence.get("refund_transaction_id", "REFUND-554433"),
                        "amount": float(evidence.get("refund_amount", val)),
                        "status": "COMPLETED",
                    }
                )

            policy_signed = bool(evidence.get("merchant_return_policy_signed", False))
            comms = bool(evidence.get("customer_comms_present", False))

            order = MerchantOrderRecord(
                order_id="ORD-FIXTURE",
                transaction_id="TXN-FIXTURE",
                buyer_email="buyer@example.com",
                shipping_address={"country_code": "US", "postal_code": "94107"},
                carrier="USPS",
                tracking_number="9400111899223197428490",
                delivery_status="DELIVERED",
                shipped_date="2026-10-20T10:00:00Z",
                refund_history=refund_history,
            )
            return SellerProtectionEngine.evaluate(
                dispute,
                order,
                customer_comms_present=comms,
                merchant_return_policy_signed=policy_signed,
            )

        order_fallback = MerchantOrderRecord(
            order_id="ORD-FIXTURE",
            transaction_id="TXN-FIXTURE",
            buyer_email="buyer@example.com",
            shipping_address={"country_code": "US", "postal_code": "94107"},
            carrier="USPS",
            tracking_number="9400111899223197428490",
            delivery_status="DELIVERED",
            shipped_date="2026-10-20T10:00:00Z",
        )
        return SellerProtectionEngine.evaluate(dispute, order_fallback)
