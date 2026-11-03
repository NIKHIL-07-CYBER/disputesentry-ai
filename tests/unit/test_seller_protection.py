"""Unit test suite for PayPal Seller Protection policy rule engine (S05).

Verifies coverage for:
- DSP007: INR delivery verification and recipient postal code matching.
- DSP008: Unauthorised dispute shipment date check prior to notification.
- DSP009: SNAD refund history and return policy evaluation.
- Boundary and negative conditions: ZIP+4 normalization, carrier status case insensitivity,
  missing shipment date, and mismatched delivery address.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

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
from app.domain.seller_protection import (
    ProtectionEvaluationResult,
    SellerProtectionEngine,
    normalize_postal_code,
    postal_codes_match,
)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "catalog" / "fixtures"


def _make_dispute(
    reason: DisputeReason,
    create_time: str = "2026-10-28T10:00:00Z",
    amount: float = 75.0,
) -> DisputeRecord:
    """Helper to create minimal valid DisputeRecord for testing."""
    return DisputeRecord(
        dispute_id="PP-D-TEST-001",
        create_time=create_time,
        reason=reason,
        status=DisputeStatus.WAITING_FOR_SELLER_RESPONSE,
        dispute_life_cycle_stage=DisputeLifeCycleStage.CHARGEBACK,
        dispute_amount=Money(currency="USD", value=amount),
        seller_response_due_date="2026-11-10T00:00:00Z",
    )


def _make_order(
    carrier: str = "USPS",
    tracking_number: str = "9400111899223197428490",
    delivery_status: str = "DELIVERED",
    shipped_date: str = "2026-10-25T09:00:00Z",
    delivery_date: str | None = "2026-10-26T15:20:00Z",
    postal_code: str = "94107",
    delivery_postal_code: str | None = None,
    refund_history: list[dict[str, object]] | None = None,
) -> MerchantOrderRecord:
    """Helper to create minimal valid MerchantOrderRecord for testing."""
    address: dict[str, str] = {
        "country_code": "US",
        "postal_code": postal_code,
    }
    if delivery_postal_code is not None:
        address["delivery_postal_code"] = delivery_postal_code

    return MerchantOrderRecord(
        order_id="ORD-TEST-100",
        transaction_id="TXN-TEST-100",
        buyer_email="buyer@example.com",
        shipping_address=address,
        carrier=carrier,
        tracking_number=tracking_number,
        delivery_status=delivery_status,
        shipped_date=shipped_date,
        delivery_date=delivery_date,
        refund_history=refund_history or [],
    )


# ---------------------------------------------------------------------------
# S05 Core Specification Tests (T05-01 through T05-05)
# ---------------------------------------------------------------------------


def test_t05_01_inr_delivery_verified_dsp007() -> None:
    """T05-01: INR delivery verified with DELIVERED status and matching postal code (DSP007)."""
    fixture_path = FIXTURES_DIR / "DSP007" / "good.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert isinstance(result, ProtectionEvaluationResult)
    assert result.eligibility == ProtectionEligibility.ELIGIBLE
    assert result.seller_protection_eligible is True
    assert result.recommended_action == RecommendedAction.CONTEST
    assert result.win_probability >= 0.90
    assert result.evidence_type == "PROOF_OF_FULFILLMENT"
    assert len(result.reasons) > 0


def test_t05_02_inr_not_delivered_dsp007() -> None:
    """T05-02: INR not delivered with PRE_SHIPMENT status (DSP007)."""
    fixture_path = FIXTURES_DIR / "DSP007" / "bad.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.seller_protection_eligible is False
    assert result.recommended_action == RecommendedAction.CONCEDE
    assert result.win_probability <= 0.10


def test_t05_03_unauthorised_prior_shipment_dsp008() -> None:
    """T05-03: Unauthorised dispute with shipment prior to notification (DSP008)."""
    fixture_path = FIXTURES_DIR / "DSP008" / "good.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert result.eligibility == ProtectionEligibility.ELIGIBLE
    assert result.seller_protection_eligible is True
    assert result.recommended_action == RecommendedAction.CONTEST
    assert result.win_probability >= 0.85
    assert result.evidence_type == "PROOF_OF_FULFILLMENT"


def test_t05_04_unauthorised_late_shipment_dsp008() -> None:
    """T05-04: Unauthorised dispute with shipment after notification (DSP008)."""
    fixture_path = FIXTURES_DIR / "DSP008" / "bad.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.seller_protection_eligible is False
    assert result.recommended_action == RecommendedAction.CONCEDE
    assert result.win_probability <= 0.05


def test_t05_05_snad_prior_refund_dsp009() -> None:
    """T05-05: SNAD dispute with prior full refund issued (DSP009)."""
    fixture_path = FIXTURES_DIR / "DSP009" / "good.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert result.eligibility == ProtectionEligibility.ELIGIBLE
    assert result.seller_protection_eligible is True
    assert result.evidence_type == "PROOF_OF_REFUND"
    assert result.win_probability >= 0.95
    assert result.recommended_action == RecommendedAction.CONTEST


def test_snad_bad_case_no_refund_acknowledged_damage_dsp009() -> None:
    """SNAD dispute without prior refund and unarranged damage (DSP009 bad)."""
    fixture_path = FIXTURES_DIR / "DSP009" / "bad.json"
    data = json.loads(fixture_path.read_text(encoding="utf-8"))

    result = SellerProtectionEngine.evaluate_fixture(data)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.seller_protection_eligible is False
    assert result.evidence_type == "NONE"
    assert result.win_probability <= 0.20
    assert result.recommended_action == RecommendedAction.CONCEDE


# ---------------------------------------------------------------------------
# Direct Domain Evaluation & In-Transit / Policy Tests
# ---------------------------------------------------------------------------


def test_inr_in_transit_tier() -> None:
    """In-transit shipment qualifies for PARTIALLY_ELIGIBLE tier with contest recommendation."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)
    order = _make_order(delivery_status="IN_TRANSIT", delivery_date=None)

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.PARTIALLY_ELIGIBLE
    assert result.seller_protection_eligible is False
    assert result.recommended_action == RecommendedAction.CONTEST
    assert 0.55 <= result.win_probability <= 0.65
    assert result.evidence_type == "PROOF_OF_FULFILLMENT"


def test_snad_return_policy_agreement() -> None:
    """SNAD with signed return policy and no prior refund provides partial eligibility."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED)
    order = _make_order(refund_history=[])

    result = SellerProtectionEngine.evaluate(
        dispute,
        order,
        merchant_return_policy_signed=True,
    )

    assert result.eligibility == ProtectionEligibility.PARTIALLY_ELIGIBLE
    assert result.evidence_type == "MERCHANT_RETURN_POLICY"
    assert result.recommended_action in (
        RecommendedAction.CONTEST,
        RecommendedAction.INQUIRY_OFFER,
    )
    assert 0.55 <= result.win_probability <= 0.65


# ---------------------------------------------------------------------------
# Positive Cases: Carrier Formats and Case Normalization
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "carrier_status",
    ["delivered", "Delivered", "DELIVERED", " Delivered "],
)
def test_carrier_status_case_and_whitespace_normalization(carrier_status: str) -> None:
    """Carrier status check is case-insensitive and trims surrounding whitespace."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)
    order = _make_order(delivery_status=carrier_status)

    result = SellerProtectionEngine.evaluate(dispute, order)
    assert result.eligibility == ProtectionEligibility.ELIGIBLE
    assert result.win_probability >= 0.90


@pytest.mark.parametrize("carrier", ["USPS", "UPS", "FedEx", "DHL", "Royal Mail"])
def test_supported_carrier_tracking(carrier: str) -> None:
    """Major carrier tracking records are supported seamlessly."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)
    order = _make_order(carrier=carrier, delivery_status="DELIVERED")

    result = SellerProtectionEngine.evaluate(dispute, order)
    assert result.eligibility == ProtectionEligibility.ELIGIBLE


# ---------------------------------------------------------------------------
# Negative Cases: Address Mismatch, Missing Dates, Missing Order
# ---------------------------------------------------------------------------


def test_negative_inr_postal_code_mismatch() -> None:
    """Mismatched postal code triggers INELIGIBLE for INR disputes."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)
    order = _make_order(
        delivery_status="DELIVERED",
        postal_code="94107",
        delivery_postal_code="90210",
    )

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.seller_protection_eligible is False
    assert result.recommended_action == RecommendedAction.CONCEDE
    assert result.win_probability <= 0.05
    assert any("postal code" in r.lower() for r in result.reasons)


def test_negative_unauthorised_missing_shipment_date() -> None:
    """Missing or unparseable shipment date triggers INELIGIBLE for Unauthorised claims."""
    dispute = _make_dispute(DisputeReason.UNAUTHORISED)
    order_whitespace = _make_order(shipped_date="   ")
    order_unparseable = _make_order(shipped_date="UNRECORDED")

    result1 = SellerProtectionEngine.evaluate(dispute, order_whitespace)
    result2 = SellerProtectionEngine.evaluate(dispute, order_unparseable)

    assert result1.eligibility == ProtectionEligibility.INELIGIBLE
    assert result1.seller_protection_eligible is False
    assert result1.recommended_action == RecommendedAction.CONCEDE
    assert result1.win_probability <= 0.05

    assert result2.eligibility == ProtectionEligibility.INELIGIBLE
    assert result2.seller_protection_eligible is False
    assert result2.recommended_action == RecommendedAction.CONCEDE
    assert result2.win_probability <= 0.05


def test_negative_unauthorised_shipping_address_mismatch() -> None:
    """Shipment to redirected address not on PayPal transaction details voids protection."""
    dispute = _make_dispute(DisputeReason.UNAUTHORISED)
    order = _make_order(shipped_date="2026-10-25T10:00:00Z")

    result = SellerProtectionEngine.evaluate(
        dispute,
        order,
        shipping_address_matches_paypal=False,
    )

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.recommended_action == RecommendedAction.CONCEDE
    assert result.win_probability <= 0.05


def test_negative_missing_order_record() -> None:
    """If no merchant order record exists, evaluation marks dispute INELIGIBLE."""
    dispute = _make_dispute(DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED)

    result = SellerProtectionEngine.evaluate(dispute, None)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.recommended_action == RecommendedAction.CONCEDE
    assert result.win_probability <= 0.05
    assert result.evidence_type == "NONE"


def test_negative_unhandled_dispute_reason() -> None:
    """Dispute reason not covered by Seller Protection returns safe fallback."""
    dispute = _make_dispute(DisputeReason.CREDIT_NOT_PROCESSED)
    order = _make_order()

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.recommended_action == RecommendedAction.CONCEDE


# ---------------------------------------------------------------------------
# Boundary Cases: ZIP+4 Matching, Whitespace Stripping, Same-Hour Timestamps
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("shipping_zip", "delivery_zip", "expected_match"),
    [
        ("90210-1234", "90210", True),
        ("90210", "90210-1234", True),
        ("94107", "94107", True),
        ("SW1A 1AA", "SW1A1AA", True),
        ("78701", "78702", False),
        ("", "90210", False),
        ("90210", None, False),
    ],
)
def test_postal_code_normalization_and_matching(
    shipping_zip: str,
    delivery_zip: str | None,
    expected_match: bool,
) -> None:
    """Postal code matching correctly normalizes spaces, hyphens, and ZIP+4 formats."""
    assert postal_codes_match(shipping_zip, delivery_zip) is expected_match
    assert normalize_postal_code(" 90210-1234 ") == "902101234"


def test_boundary_shipped_exact_same_hour_prior_timestamp() -> None:
    """Shipment dispatch minutes before dispute notification in the same hour is eligible."""
    dispute = _make_dispute(
        DisputeReason.UNAUTHORISED,
        create_time="2026-10-28T14:30:00Z",
    )
    order = _make_order(shipped_date="2026-10-28T14:15:00Z")

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.ELIGIBLE
    assert result.recommended_action == RecommendedAction.CONTEST


def test_boundary_shipped_after_dispute_in_same_hour() -> None:
    """Shipment dispatch minutes after dispute notification in the same hour is ineligible."""
    dispute = _make_dispute(
        DisputeReason.UNAUTHORISED,
        create_time="2026-10-28T14:30:00Z",
    )
    order = _make_order(shipped_date="2026-10-28T14:45:00Z")

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.recommended_action == RecommendedAction.CONCEDE


def test_inr_delivered_after_dispute_creation() -> None:
    """Delivery occurring after the dispute was opened does not qualify for full protection."""
    dispute = _make_dispute(
        DisputeReason.MERCHANDISE_OR_SERVICE_NOT_RECEIVED,
        create_time="2026-10-25T10:00:00Z",
    )
    order = _make_order(
        delivery_status="DELIVERED",
        delivery_date="2026-10-26T15:00:00Z",
    )

    result = SellerProtectionEngine.evaluate(dispute, order)

    assert result.eligibility == ProtectionEligibility.INELIGIBLE
    assert result.recommended_action == RecommendedAction.CONCEDE
