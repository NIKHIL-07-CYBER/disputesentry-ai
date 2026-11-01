# ADR-003: Scope, Non-Goals, and Version Policy
Status: accepted
Date: 2026-11-01

## Context
Clear boundaries are vital for completing a robust, fully verified deliverable within the 11-day hackathon timeframe [17][18]. Scope creep into complex card network pre-arbitration rules or multi-processor integrations risks shipping unverified code and failing the core judging criteria [43].

Sources:
- PayPal Disputes API v1: https://developer.paypal.com/platforms/disputes/handle-disputes/use-disputes-api
- Python Release Cycle & Support Policy: https://devguide.python.org/versions/
- SQLite Version History: https://www.sqlite.org/chronology.html

## Decision

### 1. MVP Scope
DisputeSentry AI v1 focuses strictly on end-to-end automation of PayPal merchant disputes in the PayPal Developer Sandbox environment, covering:
1. **Webhook Ingestion**: Full cryptographic verification, deduplication, and parsing for `CUSTOMER.DISPUTE.CREATED`, `CUSTOMER.DISPUTE.UPDATED`, and `CUSTOMER.DISPUTE.RESOLVED` [6][11].
2. **Dispute Ingestion & Lifecycle Support**:
   - Stages: `INQUIRY` and `CHARGEBACK` (with read-only visibility for `PRE_ARBITRATION` and `ARBITRATION`) [2].
   - Statuses: Active handling of `WAITING_FOR_SELLER_RESPONSE` and `UNDER_REVIEW`.
   - Core Dispute Reasons:
     - `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` (Item Not Received / INR)
     - `UNAUTHORISED` (Unauthorized Transaction)
     - `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED` (Significantly Not As Described / SNAD)
3. **Evidence Matching Engine**:
   - Queries seeded merchant SQLite records for order details, carrier tracking (USPS, FedEx, UPS), delivery timestamps, recipient address, and customer notes [10].
   - Verifies Seller Protection prerequisites (carrier online tracking status, delivery confirmation to transaction address) [10].
4. **Economic Decision Engine**:
   - Evaluates whether to `CONTEST` with compiled evidence or `CONCEDE` (accept claim) based on Net Expected Recovery ROI calculation against standard dispute fees ($15) and chargeback fees ($20) [22][26].
5. **Human-in-the-Loop Approval Gate**:
   - Enforces human authorization before executing any action if:
     - Dispute amount $\ge \$100.00$ (configurable via `APPROVAL_THRESHOLD_USD`)
     - Decision confidence $\le 0.65$
     - Proposed action is `CONCEDE` for a dispute with valid merchant delivery proof.
   - Includes deadline safeguard: triggers alert if an approval remains pending within 24 hours of `seller_response_due_date` [2][39].
6. **Execution Engine**:
   - Calls official PayPal API endpoints: `provide-evidence` (multipart and tracking payloads) and `accept-claim` [2][4][5].
7. **Audit & Dashboard**:
   - Immutable audit trail recording every webhook received, LLM evaluation, operator approval, and API response.
   - Real-time dashboard showing disputes sorted by urgency (`seller_response_due_date`) and financial exposure, displaying win rate and net recovery metrics [26].

### 2. Explicit Non-Goals
1. **No Live Production Funds**: The system operates exclusively against PayPal Sandbox; production credentials and live funds transfers are strictly prohibited in v1.
2. **No Multi-Processor Support**: Stripe, Adyen, and Shopify Payments native dispute handling are excluded from v1.
3. **No Secondary Appeals or Arbitration Filings**: The system will not automate filing secondary appeals, pre-arbitration hearings, or formal legal disputes once a claim has closed against the merchant [2][9].
4. **No Offline Statistical ML Training**: No training of custom machine learning models on private chargeback corpora; decisioning relies on deterministic rule verification augmented by structured zero-shot LLM reasoning [34].
5. **No Automatic High-Value Concession**: Under no circumstances will the system automatically accept a claim or concede money above the configured human approval threshold without explicit operator signoff [38][39].

### 3. Supported Versions & Environment Standards
- **Runtime Environment**: Python 3.11, 3.12, and 3.13 (Python 3.11+ minimum required).
- **Database Engine**: SQLite 3.35.0+ (bundled with standard Python 3.11+ runtime).
- **Target OS**: Linux (x86_64, aarch64 / Ubuntu 22.04+), macOS 13+ (Apple Silicon & Intel), Windows 10/11.
- **PayPal APIs**: PayPal REST API v1 (`Disputes API v1`, `Notifications Webhooks API v1`).
- **Browsers Supported**: Modern evergreen browsers (Chrome 115+, Firefox 115+, Safari 17+, Edge 115+).

## Alternatives considered
- **Supporting all PayPal Dispute Reasons in v1 (e.g. Canceled Recurring Billing, Incorrect Amount, Credit Not Processed)**:
  - *Why it lost:* 85%+ of e-commerce physical goods disputes are INR, Unauthorised, or SNAD. Expanding to subscription billing introduces extensive recurring mandate verification logic that would dilute focus and test quality.

## Consequences
- **Positive:**
  - Clear, attainable, high-value product deliverable completed with 100% test fixture coverage and verifiable demo behavior.
  - Eliminates ambiguity regarding payment network rules and out-of-scope processor quirks.
- **Negative / Constraints to Watch:**
  - Merchants with intangible/digital goods or subscription SaaS models will encounter reasons outside the v1 automated evidence compiler (system safely flags these for manual operator handling).
