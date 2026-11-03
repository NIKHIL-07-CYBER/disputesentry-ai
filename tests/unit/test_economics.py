"""Unit tests for the Economic Decision & Net Recovery ROI Engine (S06, DSP011, DSP012)."""

from __future__ import annotations

import pytest

from app.config import AppConfig
from app.domain.economics import EconomicEngine
from app.domain.models import RecommendedAction


def test_t06_01_positive_roi_contest_recommendation() -> None:
    """T06-01 (DSP011): A=$150.00, P_win=0.85, F=$15.00, C=$5.00 -> EV=120.25 > 0, CONTEST."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    decision = engine.evaluate(amount=150.0, win_probability=0.85, stage="CLAIM")

    # EV = (0.85 * 150) - (0.15 * 15) - 5 = 127.50 - 2.25 - 5.00 = 120.25
    assert decision.expected_value == 120.25
    assert decision.recommended_action == RecommendedAction.CONTEST
    assert decision.break_even_win_probability == pytest.approx(20.0 / 165.0, abs=1e-4)
    assert decision.break_even_probability == decision.break_even_win_probability
    assert decision.rationale == decision.justification
    assert "Positive expected net recovery ($120.25)" in decision.justification


def test_t06_02_negative_roi_concede_recommendation() -> None:
    """T06-02 (DSP011): A=$10.00, P_win=0.30, F=$15.00, C=$5.00 -> EV=-12.50 <= 0, CONCEDE."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    decision = engine.evaluate(amount=10.0, win_probability=0.30, stage="CLAIM")

    # EV = (0.30 * 10) - (0.70 * 15) - 5 = 3.00 - 10.50 - 5.00 = -12.50
    assert decision.expected_value == -12.50
    assert decision.recommended_action == RecommendedAction.CONCEDE
    assert "Negative expected net recovery (-$12.50)" in decision.justification


def test_t06_03_inquiry_stage_settlement_offer() -> None:
    """T06-03 (DSP012): Stage is INQUIRY, amount $40.00, customer requests partial compensation."""
    engine = EconomicEngine()
    decision = engine.evaluate(
        amount=40.0,
        win_probability=0.50,
        stage="INQUIRY",
        customer_requested_partial_refund=True,
    )

    assert decision.recommended_action == RecommendedAction.INQUIRY_OFFER
    assert decision.offer_amount == 20.00
    assert "Inquiry settlement offer of $20.00" in decision.justification


def test_chargeback_stage_fee_applied() -> None:
    """In CHARGEBACK stage, default dispute fee is $20.00 rather than $15.00."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    # A=150, P=0.85, F=20.00, C=5.00 -> EV = (0.85*150) - (0.15*20) - 5 = 127.50 - 3.00 - 5 = 119.50
    decision = engine.evaluate(amount=150.0, win_probability=0.85, stage="CHARGEBACK")

    assert decision.expected_value == 119.50
    assert decision.recommended_action == RecommendedAction.CONTEST


def test_custom_fee_and_overhead_override() -> None:
    """Explicitly provided fee and labor overhead override engine defaults."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    decision = engine.evaluate(
        amount=100.0,
        win_probability=0.70,
        stage="CLAIM",
        fee=25.0,
        labor_cost=10.0,
    )
    # EV = (0.70 * 100) - (0.30 * 25) - 10 = 70.00 - 7.50 - 10.00 = 52.50
    assert decision.expected_value == 52.50
    assert decision.recommended_action == RecommendedAction.CONTEST


def test_ev_boundary_zero_defaults_to_concede() -> None:
    """EV exactly equal to 0.00 must default to CONCEDE to avoid unprofitable labor."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    # P * (A + F) = F + C -> For A=80, F=15, C=5: A+F=95, F+C=20, P = 20/95
    p_zero = 20.0 / 95.0
    decision = engine.evaluate(amount=80.0, win_probability=p_zero, stage="CLAIM")

    assert decision.expected_value == 0.00
    assert decision.recommended_action == RecommendedAction.CONCEDE


def test_negative_dispute_amount_raises_error() -> None:
    """Negative dispute amount must raise ValueError."""
    engine = EconomicEngine()
    with pytest.raises(ValueError, match="amount"):
        engine.evaluate(amount=-10.0, win_probability=0.5, stage="CLAIM")


def test_invalid_win_probability_raises_error() -> None:
    """Win probability outside [0.0, 1.0] must raise ValueError."""
    engine = EconomicEngine()
    with pytest.raises(ValueError, match="win_probability"):
        engine.evaluate(amount=100.0, win_probability=-0.1, stage="CLAIM")

    with pytest.raises(ValueError, match="win_probability"):
        engine.evaluate(amount=100.0, win_probability=1.05, stage="CLAIM")


def test_zero_amount_dispute_edge_case() -> None:
    """A=$0.00 dispute results in negative EV and impossible break-even probability > 1.0."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    decision = engine.evaluate(amount=0.0, win_probability=0.5, stage="CLAIM")

    # EV = (0.5 * 0) - (0.5 * 15) - 5 = -12.50
    assert decision.expected_value == -12.50
    assert decision.recommended_action == RecommendedAction.CONCEDE
    # Break-even = (15 + 5) / (0 + 15) = 20/15 = 1.3333 > 1.0
    assert decision.break_even_win_probability > 1.0


def test_zero_amount_and_zero_fee_edge_case() -> None:
    """When amount + fee == 0.0, break even probability defaults to 1.0."""
    engine = EconomicEngine(standard_fee=0.0, labor_cost=0.0)
    decision = engine.evaluate(amount=0.0, win_probability=0.5, stage="CLAIM", fee=0.0)
    assert decision.break_even_win_probability == 1.0


def test_high_value_dispute_no_overflow() -> None:
    """Large dispute amounts (e.g., $10,000.00) compute without float precision error."""
    engine = EconomicEngine(standard_fee=15.0, labor_cost=5.0)
    decision = engine.evaluate(amount=10000.0, win_probability=0.99, stage="CLAIM")

    # EV = (0.99 * 10000) - (0.01 * 15) - 5 = 9900 - 0.15 - 5 = 9894.85
    assert decision.expected_value == 9894.85
    assert decision.recommended_action == RecommendedAction.CONTEST


def test_evaluate_inquiry_action_permissions() -> None:
    """Inquiry messaging action is permitted only in INQUIRY stage (DSP012)."""
    # Good inquiry stage
    good_res = EconomicEngine.evaluate_inquiry_action(
        stage="INQUIRY",
        dispute_id="PP-D-1012",
        message_text="Tracking proof delivered",
    )
    assert good_res.action_permitted is True
    assert good_res.api_endpoint == "POST /v1/customer/disputes/PP-D-1012/send-message"
    assert good_res.outcome == "message_dispatched"

    # Bad chargeback stage
    bad_res = EconomicEngine.evaluate_inquiry_action(
        stage="CHARGEBACK",
        dispute_id="PP-D-1012",
        message_text="Please cancel",
    )
    assert bad_res.action_permitted is False
    assert bad_res.outcome == "ACTION_NOT_PERMITTED_IN_STAGE"
    assert "INQUIRY lifecycle stage" in str(bad_res.notes)


def test_default_config_integration() -> None:
    """EconomicEngine without arguments loads thresholds from AppConfig."""
    cfg = AppConfig()
    engine = EconomicEngine()
    assert engine.standard_fee == cfg.standard_dispute_fee_usd
    assert engine.labor_cost == cfg.overhead_labor_cost_usd


def test_evaluate_fixture_dsp011() -> None:
    """evaluate_fixture correctly extracts fields from catalog fixture format."""
    engine = EconomicEngine()
    good_fixture = {
        "dispute_amount": 150.00,
        "win_probability": 0.85,
        "dispute_fee": 20.00,
        "overhead_cost": 5.00,
    }
    decision = engine.evaluate_fixture(good_fixture)
    assert decision.expected_value == 119.50
    assert decision.recommended_action == RecommendedAction.CONTEST
    expected_good_rationale = (
        "Positive expected net recovery ($119.50) strongly favors representment."
    )
    assert decision.justification == expected_good_rationale

    bad_fixture = {
        "dispute_amount": 18.00,
        "win_probability": 0.25,
        "dispute_fee": 20.00,
        "overhead_cost": 5.00,
    }
    decision_bad = engine.evaluate_fixture(bad_fixture)
    assert decision_bad.expected_value == -15.50
    assert decision_bad.recommended_action == RecommendedAction.CONCEDE
    expected_bad_rationale = (
        "Negative expected net recovery (-$15.50) means "
        "contesting will lose more in fees than accepting."
    )
    assert decision_bad.justification == expected_bad_rationale
