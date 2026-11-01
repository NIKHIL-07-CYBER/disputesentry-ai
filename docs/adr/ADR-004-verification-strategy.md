# ADR-004: Verification Strategy
Status: accepted
Date: 2026-11-01

## Context
In agentic coding, AI-generated code is only as reliable as the ground truth against which it is verified. Without strict, deterministic ground truth, subtle defects in financial calculations, API payload formatting, or cryptographic signature checks propagate undetected.

Sources:
- PayPal Disputes API v1 Specification: https://developer.paypal.com/platforms/disputes/handle-disputes/use-disputes-api
- PayPal Seller Protection Policy: https://www.paypal.com/us/webapps/mpp/ua/seller-protection
- PayPal Webhook Verification Documentation: https://docs.paypal.ai/reference/api/rest/verify-webhook-signature/verify-webhook-signature
- PCI DSS v4.0 Scoping & Tokenization: https://www.pcisecuritystandards.org/

## Decision

Every component in DisputeSentry AI is bound to a defined, authoritative ground truth and verified through an automated test harness before code is accepted.

### Component Ground Truth Matrix

| Component | Ground Truth Authority | Verification Method | Pass/Fail Criteria |
|---|---|---|---|
| **Webhook Ingestion & Sig Verification** | PayPal Webhooks v1 Spec & X.509 RFC 5280 | Golden test fixtures (`good` signed payload, `bad` tampered body, expired cert URL) | Valid signature accepted with 200 OK; tampered signature rejected with 400/401; duplicate `transmission_id` deduplicated. |
| **Merchant Record Lookup** | Seeded SQLite Schema & Order Registry | Contract test fixtures with known matching and non-matching order keys | Exact record match on `transaction_id` or `invoice_id`; returns structured `MerchantEvidencePackage` or explicit `NotFound`. |
| **Seller Protection Rule Engine** | PayPal Seller Protection Policy (Physical Goods) | Deterministic rule test suite testing address match, carrier status (`DELIVERED`), and ship date | Returns `ELIGIBLE`, `PARTIALLY_ELIGIBLE`, or `INELIGIBLE` matching ground truth policy. |
| **Economic Decision Engine (ROI)** | Mathematical Expected Value Equation: $\text{EV} = (P_{\text{win}} \cdot A) - ((1 - P_{\text{win}}) \cdot F) - C$ | Parameterized table tests over boundary conditions (low value, high fee, high $P_{\text{win}}$) | Recommended action matches expected outcome: `CONTEST` when $\text{EV} > 0$; `CONCEDE` when $\text{EV} \le 0$. |
| **AI Structured Reasoning** | Pydantic v2 Schema (`DisputeDecisionOutput`) & Frozen Eval Benchmark | Frozen test suite of 10 synthesized dispute scenarios (happy path, edge cases, adversarial prompt injections) | Strict JSON schema conformance; 100% rejection of prompt injection overrides; non-empty verifiable justification. |
| **Human-in-the-Loop State Machine** | Formal Finite State Machine specification (`docs/SPEC.md`) | Property and state transition tests with simulated time advance | State transitions strictly follow allowed paths; locks state during approval; timeout within 24h of deadline executes fail-safe fallback. |
| **PayPal API REST Client** | Official PayPal Disputes API v1 OpenAPI Specification | HTTP contract mocks (`respx` / `pytest-httpx`) + Live Sandbox verification suite | Request payloads (multipart, JSON headers) match PayPal schema; handles 401 token refresh and 400 error bodies gracefully. |
| **PCI DSS & PII Redaction** | PCI DSS v4.0 Sensitive Auth Data & PAN rules | Regex & pattern validation over all inbound/outbound strings | Zero 13-19 digit card numbers (Luhn-valid) or CVV strings present in prompts, logs, or stored evidence. |

### What Cannot Be Mechanically Verified (Human Review Protocol)
1. **User Interface Visual Polish & Layout**:
   - *Protocol:* Manual inspection against Chrome and Firefox desktop viewports; adherence to Tailwind/UI design checklist.
2. **Hackathon Video Presentation & Demo Narrative**:
   - *Protocol:* Human review of screen recording timing (< 3 minutes), audio clarity, and mandatory PayPal sandbox flow demonstration [18][42].
3. **Subjective Tone in Merchant-to-Buyer Inquiries**:
   - *Protocol:* Qualitative inspection ensuring polite, professional tone without concession of liability.

## Alternatives considered
- **Relying solely on Live PayPal Sandbox API during CI runs**:
  - *Why it lost:* Sandbox APIs experience intermittent network latency, rate limits, and outages. Relying solely on live network calls causes flaky CI builds. We use recorded golden contract mocks for CI and reserve live sandbox runs for an explicit verification stage.
- **Unchecked LLM Free-form Text Output**:
  - *Why it lost:* LLMs can hallucinate non-existent API actions or return invalid JSON. Constraining outputs to Pydantic v2 models provides compile-time and runtime guarantees.

## Consequences
- **Positive:**
  - Complete determinism in CI: 100% of core business rules, calculations, and security sanitizers can run offline in seconds.
  - Clear bug isolation: when a test fails, the defect is localized to a single component and its ground truth contract.
- **Negative / Constraints to Watch:**
  - Mock contracts must be kept strictly updated against PayPal API schema changes.
