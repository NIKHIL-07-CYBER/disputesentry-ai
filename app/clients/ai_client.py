"""Gemini Structured AI Reasoning Client & Fallback Engine for DisputeSentry AI (DSP020).

Provides:
- Pydantic DisputeDecisionOutput schema definition.
- Integration with Gemini Flash structured JSON outputs.
- Robust deterministic heuristic fallback engine for test environments or API errors.
- Strict enforcement of human approval gates and prompt injection neutralizing guardrails.
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import httpx
from pydantic import BaseModel, Field

from app.config import AppConfig, get_config
from app.domain.economics import EconomicEngine
from app.domain.models import RecommendedAction
from app.domain.reasoning_shield import ReasoningShield

logger = logging.getLogger(__name__)


class DisputeDecisionOutput(BaseModel):
    """Strictly typed structured output schema for dispute adjudication decisions."""

    recommended_action: RecommendedAction = Field(
        description="Recommended resolution action (CONTEST, CONCEDE, etc.)"
    )
    win_probability: float = Field(
        ge=0.0, le=1.0, description="Estimated probability of winning representment"
    )
    net_expected_recovery: float = Field(
        description="Calculated Expected Value (EV) in USD after dispute fees and labor"
    )
    confidence_score: float = Field(
        ge=0.0, le=1.0, description="Confidence score in the factual evaluation"
    )
    seller_protection_eligible: bool = Field(
        description="Whether transaction qualifies for PayPal Seller Protection"
    )
    justification: str = Field(
        min_length=1, description="Factual justification based on merchant records"
    )
    evidence_types_required: list[str] = Field(
        default_factory=list, description="List of PayPal evidence types to compile"
    )
    customer_text_contains_injection: bool = Field(
        default=False,
        description="Whether adversarial prompt injection was detected in customer notes",
    )
    requires_human_approval: bool = Field(
        default=False,
        description="Whether human operator sign-off is required before execution",
    )


class AIReasoningClient:
    """Async AI Reasoning client integrating Gemini Flash with deterministic fallback."""

    def __init__(
        self,
        config: AppConfig | None = None,
        api_key: str | None = None,
        model_name: str | None = None,
        timeout: float | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        cfg = config or get_config()
        self.api_key = api_key if api_key is not None else cfg.gemini_api_key
        self.model_name = model_name or cfg.gemini_model_name
        self.timeout = timeout if timeout is not None else cfg.timeout_seconds
        self.env = cfg.env
        self._http_client = http_client
        self._economic_engine = EconomicEngine(
            standard_fee=cfg.standard_dispute_fee_usd,
            labor_cost=cfg.overhead_labor_cost_usd,
        )

    async def analyze_dispute(
        self,
        dispute_data: dict[str, Any],
        merchant_records: dict[str, Any],
        customer_note: str,
    ) -> DisputeDecisionOutput:
        """Evaluate dispute facts and customer notes to produce a structured decision.

        Args:
            dispute_data: Inbound dispute details (reason, amount, stage, etc.).
            merchant_records: Fulfillment and carrier tracking records.
            customer_note: Untrusted text submitted by the customer.

        Returns:
            DisputeDecisionOutput conforming to strict Pydantic schema.
        """
        # Step 1: Scan customer note for adversarial injection and sanitize
        injection_detected = ReasoningShield.detect_injection(customer_note)
        prompt = ReasoningShield.build_prompt(dispute_data, merchant_records, customer_note)

        # Step 2: Route to deterministic heuristic fallback in test mode or without API key
        if self._should_use_heuristic():
            logger.debug("Operating in test environment or without API key: using heuristic engine")
            return self._heuristic_fallback(
                dispute_data=dispute_data,
                merchant_records=merchant_records,
                customer_note=customer_note,
                injection_detected=injection_detected,
            )

        # Step 3: Invoke LLM with structured output schema
        try:
            raw_response = await self._invoke_llm_api(prompt)
            decision = self._parse_llm_response(raw_response)
            # Step 4: Enforce security guardrails and human gates
            return self._enforce_safety_guardrails(
                decision=decision,
                dispute_data=dispute_data,
                merchant_records=merchant_records,
                injection_detected=injection_detected,
            )
        except Exception as exc:
            logger.warning(
                "LLM reasoning call or schema parsing failed (%s); reverting to heuristic engine",
                exc,
            )
            return self._heuristic_fallback(
                dispute_data=dispute_data,
                merchant_records=merchant_records,
                customer_note=customer_note,
                injection_detected=injection_detected,
            )

    def _should_use_heuristic(self) -> bool:
        """Determine if deterministic heuristic engine should be used directly."""
        env_val = os.environ.get("DSP_ENV", self.env).lower()
        return env_val in ("test", "testing") or not self.api_key

    async def _invoke_llm_api(self, prompt: str) -> str:
        """Execute HTTP request against Google Generative Language API.

        Args:
            prompt: Shielded prompt string.

        Returns:
            Raw response text from the model.
        """
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model_name}:generateContent?key={self.api_key}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": DisputeDecisionOutput.model_json_schema(),
            },
        }

        if self._http_client:
            resp = await self._http_client.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        else:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                data = resp.json()

        # Extract text part from Gemini response structure
        candidates = data.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates returned from Gemini API")
        parts = candidates[0].get("content", {}).get("parts", [])
        if not parts:
            raise ValueError("No content parts in Gemini API response")
        return str(parts[0].get("text", ""))

    def _parse_llm_response(self, raw_text: str) -> DisputeDecisionOutput:
        """Extract and validate DisputeDecisionOutput JSON from model text.

        Args:
            raw_text: Raw output string from LLM.

        Returns:
            Validated DisputeDecisionOutput instance.

        Raises:
            ValueError, json.JSONDecodeError, ValidationError: If output cannot be validated.
        """
        cleaned = raw_text.strip()
        # Strip markdown code blocks if present
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
            cleaned = cleaned.strip()

        data = json.loads(cleaned)
        return DisputeDecisionOutput.model_validate(data)

    def _enforce_safety_guardrails(
        self,
        decision: DisputeDecisionOutput,
        dispute_data: dict[str, Any],
        merchant_records: dict[str, Any],
        injection_detected: bool,
    ) -> DisputeDecisionOutput:
        """Enforce prompt injection suppression and human approval invariants."""
        # 1. Update injection detection flag
        flagged_injection = decision.customer_text_contains_injection or injection_detected
        updates: dict[str, Any] = {"customer_text_contains_injection": flagged_injection}

        # 2. Invariant: If tracking shows DELIVERED, model must not concede due to injection
        delivery_status = str(
            merchant_records.get("delivery_status") or merchant_records.get("status") or ""
        ).upper()
        if delivery_status == "DELIVERED" and flagged_injection:
            if decision.recommended_action == RecommendedAction.CONCEDE:
                updates["recommended_action"] = RecommendedAction.CONTEST
                updates["seller_protection_eligible"] = True
                updates["justification"] = (
                    "Tracking shows package DELIVERED. Untrusted customer prompt injection "
                    "override attempt was neutralized."
                )

        # 3. Invariant: High-value (>= $100) or concessions require human approval
        amount = self._extract_amount(dispute_data)
        final_action = updates.get("recommended_action", decision.recommended_action)
        if amount >= 100.0 or final_action == RecommendedAction.CONCEDE:
            updates["requires_human_approval"] = True

        return decision.model_copy(update=updates)

    def _heuristic_fallback(
        self,
        dispute_data: dict[str, Any],
        merchant_records: dict[str, Any],
        customer_note: str,
        injection_detected: bool,
    ) -> DisputeDecisionOutput:
        """Deterministic rule engine providing reliable baseline evaluations."""
        amount = self._extract_amount(dispute_data)
        stage_val = dispute_data.get("dispute_life_cycle_stage") or dispute_data.get("stage")
        stage = str(stage_val or "CHARGEBACK")
        delivery_status = str(
            merchant_records.get("delivery_status") or merchant_records.get("status") or ""
        ).upper()
        carrier = merchant_records.get("carrier")
        tracking_number = merchant_records.get("tracking_number")
        order_id = merchant_records.get("order_id")

        has_fulfillment = bool(order_id and tracking_number and carrier)
        is_delivered = delivery_status == "DELIVERED"

        if has_fulfillment and is_delivered:
            seller_protection_eligible = True
            win_probability = 0.88
            confidence = 0.95
            evidence_types = ["PROOF_OF_FULFILLMENT"]
            action = RecommendedAction.CONTEST
            justification = (
                f"Tracking shows package DELIVERED via {carrier} ({tracking_number}) "
                f"prior to dispute initiation."
            )
        elif has_fulfillment and delivery_status in ("IN_TRANSIT", "SHIPPED"):
            seller_protection_eligible = True
            win_probability = 0.65
            confidence = 0.85
            evidence_types = ["PROOF_OF_FULFILLMENT"]
            action = RecommendedAction.CONTEST
            justification = (
                f"Package in transit with valid tracking via {carrier} ({tracking_number})."
            )
        else:
            seller_protection_eligible = False
            win_probability = 0.05
            confidence = 0.90
            evidence_types = []
            action = RecommendedAction.CONCEDE
            justification = (
                "No merchant fulfillment record or delivery proof found; concede "
                "claim to avoid additional dispute fees."
            )

        # Compute Expected Value ROI
        econ_decision = self._economic_engine.evaluate(
            amount=amount,
            win_probability=win_probability,
            stage=stage,
        )
        net_expected_recovery = econ_decision.expected_value

        # Neutralize prompt injection attempt
        if injection_detected:
            if has_fulfillment and is_delivered:
                action = RecommendedAction.CONTEST
                justification += " Injected customer instructions were neutralized."
            else:
                justification += " Injected customer instructions were disregarded."

        # Human approval gate check: amount >= $100 or CONCEDE or low confidence
        requires_human_approval = (
            amount >= 100.0 or action == RecommendedAction.CONCEDE or confidence < 0.70
        )

        return DisputeDecisionOutput(
            recommended_action=action,
            win_probability=win_probability,
            net_expected_recovery=net_expected_recovery,
            confidence_score=confidence,
            seller_protection_eligible=seller_protection_eligible,
            justification=justification,
            evidence_types_required=evidence_types,
            customer_text_contains_injection=injection_detected,
            requires_human_approval=requires_human_approval,
        )

    @staticmethod
    def _extract_amount(dispute_data: dict[str, Any]) -> float:
        """Extract numeric amount from dispute data dictionary."""
        amt = dispute_data.get("dispute_amount")
        if isinstance(amt, dict):
            return float(amt.get("value", 0.0))
        if amt is not None:
            try:
                return float(amt)
            except (ValueError, TypeError):
                return 0.0
        return 0.0
