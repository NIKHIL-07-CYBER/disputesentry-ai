"""Economic Decision & Net Expected Recovery (ROI) Engine for DisputeSentry AI (DSP011, DSP012).

Calculates Net Expected Recovery (EV) for dispute contest vs concede decisions,
computes break-even win probabilities, formulates inquiry settlement offers,
and governs lifecycle messaging permissions.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict

from app.config import AppConfig
from app.domain.models import RecommendedAction


class EconomicDecision(BaseModel):
    """Structured decision output containing Expected Value and recommended action."""

    model_config = ConfigDict(frozen=True)

    expected_value: float
    recommended_action: RecommendedAction
    break_even_win_probability: float
    justification: str
    offer_amount: float | None = None

    @property
    def rationale(self) -> str:
        """Alias for justification matching catalog fixture schema."""
        return self.justification

    @property
    def break_even_probability(self) -> float:
        """Alias for break_even_win_probability."""
        return self.break_even_win_probability


class InquiryEvaluationResult(BaseModel):
    """Evaluation result for buyer inquiry communication permission."""

    model_config = ConfigDict(frozen=True)

    action_permitted: bool
    outcome: str
    api_endpoint: str | None = None
    notes: str | None = None


class EconomicEngine:
    """Quantitative decision engine evaluating dispute representment ROI (DSP011, DSP012)."""

    def __init__(
        self,
        standard_fee: float | None = None,
        labor_cost: float | None = None,
    ) -> None:
        cfg = AppConfig()
        self.standard_fee = (
            standard_fee if standard_fee is not None else cfg.standard_dispute_fee_usd
        )
        self.labor_cost = (
            labor_cost if labor_cost is not None else cfg.overhead_labor_cost_usd
        )

    def evaluate(
        self,
        amount: float,
        win_probability: float,
        stage: str = "CLAIM",
        *,
        customer_requested_partial_refund: bool = False,
        fee: float | None = None,
        labor_cost: float | None = None,
    ) -> EconomicDecision:
        """Compute Net Expected Recovery ROI and recommend optimal resolution action.

        Formula:
            EV = (P_win * Amount) - ((1 - P_win) * Fee) - Overhead

        Args:
            amount: Disputed transaction amount (must be non-negative).
            win_probability: Estimated probability of winning (0.0 to 1.0).
            stage: Dispute lifecycle stage (e.g. INQUIRY, CLAIM, CHARGEBACK).
            customer_requested_partial_refund: Whether customer requested settlement.
            fee: Optional fee override (defaults to $20 for chargeback, $15 standard).
            labor_cost: Optional internal overhead cost override.

        Returns:
            EconomicDecision containing expected_value, action, and rationale.

        Raises:
            ValueError: If amount < 0 or win_probability is outside [0.0, 1.0].
        """
        if amount < 0.0:
            raise ValueError(f"Dispute amount must be non-negative, got {amount}")

        if not (0.0 <= win_probability <= 1.0):
            raise ValueError(
                f"win_probability must be between 0.0 and 1.0, got {win_probability}"
            )

        # Determine dispute fee
        if fee is not None:
            effective_fee = float(fee)
        elif stage.upper() == "CHARGEBACK":
            effective_fee = 20.0
        else:
            effective_fee = float(self.standard_fee)

        effective_labor = (
            float(labor_cost) if labor_cost is not None else float(self.labor_cost)
        )

        # Quantitative Net Expected Recovery: EV = (P_win * A) - ((1 - P_win) * F) - C
        ev = (
            (win_probability * amount)
            - ((1.0 - win_probability) * effective_fee)
            - effective_labor
        )
        ev = round(ev, 2)
        if abs(ev) < 1e-9:
            ev = 0.0

        # Break-even probability: P = (F + C) / (A + F)
        if (amount + effective_fee) > 0.0:
            break_even_p = (effective_fee + effective_labor) / (amount + effective_fee)
        else:
            break_even_p = 1.0

        # DSP012: Inquiry stage settlement offer
        if stage.upper() == "INQUIRY" and customer_requested_partial_refund:
            offer = round(amount * 0.5, 2)
            justification = (
                f"Inquiry settlement offer of ${offer:.2f} recommended "
                f"to resolve customer dispute before escalation."
            )
            return EconomicDecision(
                expected_value=ev,
                recommended_action=RecommendedAction.INQUIRY_OFFER,
                break_even_win_probability=break_even_p,
                justification=justification,
                offer_amount=offer,
            )

        # Decision rule: EV > 0 -> CONTEST, EV <= 0 -> CONCEDE
        if ev > 0.0:
            recommended_action = RecommendedAction.CONTEST
            justification = (
                f"Positive expected net recovery (${ev:.2f}) strongly favors representment."
            )
        else:
            recommended_action = RecommendedAction.CONCEDE
            if ev < 0.0:
                justification = (
                    f"Negative expected net recovery (-${abs(ev):.2f}) means "
                    f"contesting will lose more in fees than accepting."
                )
            else:
                justification = (
                    f"Zero expected net recovery (${ev:.2f}) means "
                    f"contesting will lose more in fees than accepting."
                )

        return EconomicDecision(
            expected_value=ev,
            recommended_action=recommended_action,
            break_even_win_probability=break_even_p,
            justification=justification,
            offer_amount=None,
        )

    def evaluate_fixture(self, fixture: dict[str, Any]) -> EconomicDecision:
        """Evaluate catalog fixture dictionary against the economic engine."""
        amount = float(fixture.get("dispute_amount", 0.0))
        win_probability = float(fixture.get("win_probability", 0.0))
        fee = float(fixture["dispute_fee"]) if "dispute_fee" in fixture else None
        labor = (
            float(fixture["overhead_cost"]) if "overhead_cost" in fixture else None
        )
        stage = str(
            fixture.get(
                "stage",
                "CHARGEBACK" if fee == 20.0 else "CLAIM",
            )
        )
        return self.evaluate(
            amount=amount,
            win_probability=win_probability,
            stage=stage,
            fee=fee,
            labor_cost=labor,
        )

    @staticmethod
    def evaluate_inquiry_action(
        stage: str,
        dispute_id: str,
        message_text: str | None = None,
    ) -> InquiryEvaluationResult:
        """Validate inquiry stage bilateral customer communication permissions (DSP012)."""
        if stage.upper() == "INQUIRY":
            return InquiryEvaluationResult(
                action_permitted=True,
                api_endpoint=f"POST /v1/customer/disputes/{dispute_id}/send-message",
                outcome="message_dispatched",
            )

        return InquiryEvaluationResult(
            action_permitted=False,
            outcome="ACTION_NOT_PERMITTED_IN_STAGE",
            notes="Inquiry messaging is exclusively available in INQUIRY lifecycle stage.",
        )
