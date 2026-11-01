# ADR-002: Integration Strategy
Status: accepted
Date: 2026-11-01

## Context
DisputeSentry AI connects PayPal's external dispute processing infrastructure, an internal merchant record system, and an AI-driven decision engine. Robustness, strict adherence to PayPal's API specifications, and defensible error handling are essential.

Specific integration boundaries:
1. **PayPal REST API v1**: Authenticated dispute operations in PayPal Sandbox (`https://api-m.sandbox.paypal.com`) [2][3][14].
2. **PayPal Webhooks Engine**: Real-time asynchronous ingestion of dispute state changes (`CUSTOMER.DISPUTE.*`) [6][7][11].
3. **Internal Merchant Record System**: Local relational store containing order fulfillment, logistics tracking, proof of delivery, and customer communications [2][10].
4. **AI Reasoning Provider**: Structured decision modeling using constrained JSON generation against untrusted customer dispute text [40][41].

Sources:
- PayPal Disputes API v1 Reference: https://developer.paypal.com/platforms/disputes/handle-disputes/use-disputes-api
- PayPal Webhook Verification: https://docs.paypal.ai/reference/api/rest/verify-webhook-signature/verify-webhook-signature
- PayPal Supported File Types & Sizes: https://docs.paypal.ai/growth/disputes/reference/supported-file-types-sizes.md
- PayPal OAuth 2.0 Client Credentials: https://developer.paypal.com/api/get-started

## Decision

### 1. PayPal REST API Client & Token Lifecycle
- **Endpoint**: Target `https://api-m.sandbox.paypal.com` (configurable to production via `PAYPAL_ENV=sandbox|live`).
- **Authentication**: `POST /v1/oauth2/token` using HTTP Basic Authentication (`PAYPAL_CLIENT_ID:PAYPAL_CLIENT_SECRET`) with `grant_type=client_credentials`.
- **Token Cache**: Tokens are cached in-memory with expiration tracking based on the returned `expires_in` seconds (default 32,400s / 9 hrs). Refresh is proactively triggered when the remaining TTL drops below 300 seconds.
- **Dispute Operations**:
  - `GET /v1/customer/disputes/{dispute_id}`: Fetches dispute lifecycle stage, status, allowed response options, and HATEOAS action links.
  - `POST /v1/customer/disputes/{dispute_id}/provide-evidence`:
    - For tracking-only submissions without attachments: submits `application/json` payload with `evidence_type: PROOF_OF_FULFILLMENT`, carrier name, and tracking number.
    - For evidence requiring files (receipts, delivery signatures): submits `multipart/form-data` with an `input` JSON part and binary attachment parts (`evidence_file_1`, etc.), validating file extensions (JPG, PNG, PDF) and size ceilings (max 10 MB per file, max 50 MB total request) [8].
  - `POST /v1/customer/disputes/{dispute_id}/accept-claim`: Submits `application/json` with optional merchant note.
  - `POST /v1/customer/disputes/{dispute_id}/send-message`: Submits buyer inquiry communication.

### 2. Webhook Signature Verification and Idempotency
- **Endpoint**: Exposed at `POST /webhooks/paypal`.
- **Verification Strategy**:
  - Dual-mode verification:
    - *Online verification mode*: Calls PayPal's `POST /v1/notifications/verify-webhook-signature` passing `auth_algo`, `cert_url`, `transmission_id`, `transmission_sig`, `transmission_time`, `webhook_id`, and the raw JSON request body [11].
    - *Local cryptographic verification mode*: Downloads and caches the certificate from `cert_url` (verifying hostname ends in `.paypal.com`), reconstructs the CRC32 digest of the raw body and transmission headers, and verifies the RSA signature using `cryptography` [11][12].
- **Idempotency Guarantee**:
  - Every incoming event is logged into `webhook_events` with `transmission_id` and `event_id`.
  - If a incoming event with an identical `transmission_id` is received, the webhook receiver logs the duplicate and immediately returns HTTP `200 OK` with `{"status": "duplicate_ignored"}` without re-triggering business logic.

### 3. Merchant Record Integration (Seeded Store)
- Merchant order history is accessed via a dedicated repository interface (`MerchantRecordRepository`).
- For MVP/v1, this repository queries a seeded SQLite database containing realistic orders, carrier tracking numbers (USPS, FedEx, UPS), delivery signatures, timestamps, and customer message history.
- The interface is isolated so that a production connector (Shopify API, WooCommerce, or custom ERP) can be dropped in without changing the core dispute decision pipeline.

### 4. AI Reasoning Engine Integration
- Invoked using schema-constrained JSON output (`google-genai` / Gemini 2.5 Structured Outputs).
- Untrusted inputs (such as buyer claims and dispute notes) are strictly delimited in prompt variables and sanitized (stripping control chars and prompt injection attempts) [41].
- The model outputs a strictly validated Pydantic model (`DisputeDecisionOutput`) containing:
  - Recommended action (`CONTEST`, `CONCEDE`, `MESSAGE`, `ESCALATE`)
  - Confidence score (0.0 to 1.0)
  - Estimated win probability ($P_{\text{win}}$)
  - Structured reasoning explanation
  - Required evidence inventory list
  - Flag indicating whether human review is mandatory

## Alternatives considered
1. **Directly Using PayPal MCP Server / Agent Toolkit for all API Actions**
   - *Why it lost:* Investigation reveals PayPal's current agent toolkit provides read tools (`list_disputes`, `get_dispute`) but lacks complete or verified mutation tools for multipart evidence upload and claim acceptance. Direct REST API calls via `httpx` provide 100% contract fidelity, predictable error handling, and complete multipart support.
2. **Unverified Local Webhook Ingestion (Bypassing Signature Checks in Sandbox)**
   - *Why it lost:* Fails the production-readiness quality bar [7][11]. Implementing full signature verification ensures the service adheres to enterprise security standards and prevents unauthorized dispute triggering.

## Consequences
- **Positive:**
  - High resilience: clear separation between webhook ingestion, dispute querying, decision synthesis, and API execution.
  - Zero third-party lock-in: direct PayPal REST API integration adheres strictly to official specifications without reliance on proprietary intermediary wrappers.
- **Negative / Constraints to Watch:**
  - PayPal's sandbox webhook delivery can experience latency; local test runners must support direct synthetic event injection for deterministic CI testing.
  - Webhook certificate URLs must be strictly validated to prevent SSRF vulnerabilities (must match `^https://api(\-m)?\.paypal\.com/` or `^https://.*\.paypal\.com/`).
