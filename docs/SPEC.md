# Product Specification: DisputeSentry AI

**Document Version:** 1.0.0  
**ID Prefix:** `DSP`  
**Catalog Item Scheme:** `DSP###` (e.g., `DSP001`, `DSP002`, ...)  
**Target Environment:** PayPal Sandbox REST API v1, Python 3.11+, SQLite 3  

---

## 1. Overview and Problem Context

DisputeSentry AI is an automated decision and resolution platform designed for merchants processing sales through PayPal. When disputes or chargebacks arise, merchants face tight, non-negotiable response deadlines (`seller_response_due_date`, typically 10 to 20 days [2][19][21]). Failure to respond within this window results in automatic default forfeiture of the transaction amount plus standard dispute fees ($15-$30) [22].

DisputeSentry AI continuously ingests PayPal dispute webhooks, links disputes to internal merchant shipment and order fulfillment records, computes an economic Net Expected Recovery ROI model, drafts evidence packages aligned with PayPal Seller Protection rules, and either executes dispute actions directly or stages them for human approval when financial exposure warrants operator oversight [10][26][38].

---

## 2. Users and Primary Personas

1. **Merchant Operator / Support Lead**:
   - Manages day-to-day dispute queues.
   - Needs automated triage so that obvious fraudulent claims with full delivery proof are contested instantly without manual overhead.
   - Requires an approval gate for high-value claims ($\ge \$100.00$) to prevent unexpected concessions or incorrect evidence submissions.
2. **Finance / Operations Director**:
   - Monitors financial recovery metrics.
   - Requires real-time visibility into dispute win rates, net recovery dollars, fee penalties, and an immutable audit trail for accounting reconciliation.
3. **Hackathon Evaluator / Judge**:
   - Evaluates system capabilities in the PayPal Sandbox environment.
   - Needs to trigger simulated webhooks or fetch sandbox disputes, observe automated decision synthesis, approve or override actions, and verify API execution against PayPal endpoints [17][42].

---

## 3. Primary System Workflows

```
                                  +-----------------------+
                                  | PayPal Webhook Engine |
                                  +-----------+-----------+
                                              |
                                              v  POST /webhooks/paypal
+---------------------------------------------------------------------------------+
| Webhook Ingestion & Verification                                                |
|  - Verify X.509 cert and RSA signature                                          |
|  - Check transmission_id in webhook_events (idempotency)                         |
|  - Return 200 OK                                                                |
+-------------------------------------+-------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
| Dispute Synchronization & Evidence Lookup                                       |
|  - GET /v1/customer/disputes/{dispute_id} from PayPal REST API                   |
|  - Query Merchant Store (orders, tracking, proof of delivery, customer comms)   |
|  - Match tracking carrier, delivery status, and buyer address                   |
+-------------------------------------+-------------------------------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
| Decision & ROI Evaluation Engine                                                |
|  - Verify PayPal Seller Protection criteria (INR, UNAUTHORISED, SNAD)            |
|  - Compute Win Probability P_win (0.0 to 1.0)                                   |
|  - Calculate Net Expected Recovery: EV = (P_win * Amount) - ((1-P_win) * Fee)    |
|  - Select Action: CONTEST | CONCEDE | MESSAGE | ESCALATE                        |
+-------------------------------------+-------------------------------------------+
                                      |
                +---------------------+---------------------+
                |                                           |
    [ Amount < $100 AND ]                       [ Amount >= $100 OR ]
    [ P_win > 0.65      ]                       [ P_win <= 0.65     ]
                |                                           |
                v                                           v
+-------------------------------+           +-------------------------------+
| Auto-Execution Pipeline       |           | Human Approval Gate           |
|  - Check allowed action links |           |  - Stage in PENDING_APPROVAL  |
|  - Call PayPal API            |           |  - Operator APPROVES/REJECTS  |
|  - Write to Audit Trail       |           |  - Deadline monitor alert     |
+---------------+---------------+           +---------------+---------------+
                |                                           |
                +---------------------+---------------------+
                                      |
                                      v
+---------------------------------------------------------------------------------+
| PayPal Disputes API Execution                                                   |
|  - provide-evidence (multipart / json tracking)                                  |
|  - accept-claim                                                                 |
|  - Record API response & update local dispute state                             |
+---------------------------------------------------------------------------------+
```

---

## 4. Interfaces and Protocols

### 4.1 CLI Commands (`disputesentry`)
The application exposes a standard command-line interface:

| Command | Arguments / Flags | Description |
|---|---|---|
| `serve` | `--host 0.0.0.0 --port 8000 --reload` | Starts the FastAPI web server, webhook listener, and merchant UI dashboard. |
| `sync` | `--dispute-id <ID> [--all]` | Synchronizes dispute state directly from PayPal Sandbox API into the local database. |
| `evaluate` | `--dispute-id <ID> [--dry-run]` | Runs the decision engine on a specific dispute and outputs structured JSON decision. |
| `seed` | `--reset` | Seeds the local SQLite database with realistic mock orders, shipments, and dispute scenarios. |
| `verify-fixtures` | `--path catalog/fixtures` | Executes test runner validating all catalog item fixtures against the decision engine. |

### 4.2 Web API Endpoints

#### 1. Webhook Ingestion
- **Route**: `POST /webhooks/paypal`
- **Headers Required**:
  - `PAYPAL-AUTH-ALGO`: e.g. `SHA256withRSA`
  - `PAYPAL-TRANSMISSION-ID`: UUID string
  - `PAYPAL-CERT-URL`: e.g. `https://api.sandbox.paypal.com/v1/notifications/certs/CERT-ID`
  - `PAYPAL-TRANSMISSION-SIG`: Base64 encoded signature
  - `PAYPAL-TRANSMISSION-TIME`: ISO-8601 timestamp string
- **Request Body**: Raw JSON payload of PayPal webhook event.
- **Responses**:
  - `200 OK`: `{"status": "processed", "event_id": "WH-...", "dispute_id": "PP-D-..."}`
  - `200 OK`: `{"status": "duplicate_ignored", "transmission_id": "..."}`
  - `400 Bad Request`: `{"error": "INVALID_SIGNATURE", "message": "Verification failed"}`
  - `422 Unprocessable Entity`: `{"error": "MALFORMED_PAYLOAD", "details": [...]}`

#### 2. Dispute Management
- **Route**: `GET /api/v1/disputes`
  - **Query Params**: `status` (optional), `stage` (optional), `limit` (default 50), `offset` (default 0).
  - **Response Schema (`DisputeListResponse`)**:
    ```json
    {
      "items": [
        {
          "dispute_id": "PP-D-14001",
          "create_time": "2026-10-30T10:00:00Z",
          "status": "WAITING_FOR_SELLER_RESPONSE",
          "dispute_stage": "CHARGEBACK",
          "dispute_amount": {"currency": "USD", "value": "149.99"},
          "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
          "seller_response_due_date": "2026-11-09T10:00:00Z",
          "decision_state": "PENDING_APPROVAL",
          "recommended_action": "CONTEST",
          "win_probability": 0.88,
          "expected_net_recovery": 128.49
        }
      ],
      "total": 1
    }
    ```
- **Route**: `GET /api/v1/disputes/{dispute_id}`
  - Returns complete dispute details, compiled merchant evidence package, decision breakdown, and audit history.
- **Route**: `POST /api/v1/disputes/{dispute_id}/approve`
  - **Request Body**: `{"operator_id": "admin", "notes": "Approved for representment"}`
  - **Response**: `200 OK` with executed action and PayPal API response status.
- **Route**: `POST /api/v1/disputes/{dispute_id}/reject`
  - **Request Body**: `{"operator_id": "admin", "reason": "Prefer to refund directly"}`
  - **Response**: `200 OK` with updated status.

#### 3. Metrics and Audit
- **Route**: `GET /api/v1/metrics`
  - Returns aggregated statistics: total disputes, win rate percentage, contested count, conceded count, total dollars recovered, total dispute fees avoided.
- **Route**: `GET /api/v1/audit-log`
  - Returns immutable chronological audit log entries.

---

## 5. Configuration and Precedence

Configuration is managed via `pydantic-settings` with strict precedence:
1. Environment variables (highest priority, prefix `DISPUTESENTRY_`)
2. Local `.env` file
3. `config.yaml` at project root
4. Built-in defaults (lowest priority)

### Configuration Schema

```yaml
server:
  host: "0.0.0.0"
  port: 8000
  log_level: "INFO"

paypal:
  mode: "sandbox"                       # sandbox | live
  client_id: "${PAYPAL_CLIENT_ID}"
  client_secret: "${PAYPAL_CLIENT_SECRET}"
  webhook_id: "${PAYPAL_WEBHOOK_ID}"
  base_url: "https://api-m.sandbox.paypal.com"
  token_refresh_buffer_seconds: 300

decision_engine:
  approval_threshold_usd: 100.00        # Disputes >= this amount require human approval
  min_confidence_auto_execute: 0.65     # Below this confidence, require human approval
  standard_dispute_fee_usd: 15.00       # Standard dispute fee
  chargeback_fee_usd: 20.00             # Chargeback fee
  overhead_labor_cost_usd: 5.00         # Estimated labor cost to assemble evidence
  deadline_alert_hours: 24              # Alert when response due date is within X hours

ai_provider:
  model_name: "gemini-2.5-flash"
  api_key: "${GEMINI_API_KEY}"
  temperature: 0.1
  timeout_seconds: 10.0

storage:
  database_path: "disputesentry.db"
  wal_mode: true
```

---

## 6. Input Handling, Validation, and Error Taxonomy

All inputs undergo strict Pydantic v2 validation. Invalid payloads are rejected at boundary interfaces before reaching core domain handlers.

### Error Code Taxonomy

| Error Code | HTTP Status | Meaning | Resolution / Safe Behavior |
|---|---|---|---|
| `UNAUTHORIZED` | 401 | Missing or invalid API credentials | Check `PAYPAL_CLIENT_ID` and `PAYPAL_CLIENT_SECRET`. |
| `INVALID_SIGNATURE` | 400 | PayPal webhook signature verification failed | Reject webhook event; log transmission details for security audit. |
| `DUPLICATE_EVENT` | 200 | Webhook transmission ID already recorded | Acknowledge with 200 OK; ignore redundant processing. |
| `DISPUTE_NOT_FOUND` | 404 | Dispute ID does not exist in local database or PayPal API | Verify dispute ID string format (`PP-D-\d+`). |
| `ACTION_NOT_PERMITTED` | 409 | Action not present in dispute's `links` or allowed options | Refuse API call; log permitted actions from PayPal dispute resource. |
| `DEADLINE_EXPIRED` | 410 | Current time past `seller_response_due_date` | Dispute cannot be contested; mark as EXPIRED; notify operator. |
| `PAYLOAD_TOO_LARGE` | 413 | Evidence file exceeds 10 MB or total multipart exceeds 50 MB | Reject file; prompt merchant to compress image/PDF before upload. |
| `PAYPAL_API_ERROR` | 502 | Upstream PayPal REST API returned 4xx/5xx | Capture PayPal error debug ID; retry idempotent GETs with exponential backoff. |

---

## 7. Non-Functional Requirements (Quantified)

1. **Webhook Processing Latency**:
   - Webhook signature verification and local persistence must complete within **1,500 ms** (99th percentile).
2. **Decision Generation Latency**:
   - End-to-end evidence matching and economic decision evaluation must complete within **5,000 ms** (95th percentile).
3. **Determinism**:
   - The economic ROI calculation and Seller Protection rule engine must be **100% deterministic**. Given identical order, tracking, and dispute parameters, the calculated Expected Value and eligibility classification must be identical across runs.
4. **Memory and Footprint**:
   - The application runtime must remain under **250 MB RSS** during active serving of API and dashboard endpoints.
5. **Storage and Concurrency**:
   - The SQLite database operates with Write-Ahead Logging (`PRAGMA journal_mode=WAL;`) enabled, supporting concurrent reader processes alongside asynchronous webhook ingestion.

---

## 8. Privacy, Security, and PCI DSS Governance

1. **Cardholder Data Redaction (PCI DSS Requirement 3.4)**:
   - DisputeSentry AI never stores, processes, or transmits Primary Account Numbers (PAN) or Sensitive Authentication Data (SAD / CVV).
   - Inbound dispute payloads, buyer comments, and evidence files are filtered through a Luhn-validated regex scrubber. Any sequence matching a 13 to 19 digit card number is permanently masked to `[REDACTED_PAN]` before database persistence or prompt inclusion [40][41].
2. **Prompt Injection Isolation**:
   - Customer dispute notes and buyer messages are classified as untrusted text [41].
   - Prompt construction isolates buyer text within fenced `<untrusted_buyer_claim>` XML blocks with system instructions forbidding tool execution or prompt override.
3. **Immutable Audit Trail**:
   - Every dispute state transition, evaluation score, operator approval, and PayPal API dispatch is recorded in an append-only `audit_log` table with timestamps, operator IDs, and SHA-256 payload hashes.

---

## 9. ID Scheme for Catalog Items

Catalog items use the prefix `DSP` followed by a three-digit sequential integer (`DSP001` through `DSP999`).
- `DSP001` - `DSP005`: Webhook ingestion, signature verification, and deduplication.
- `DSP006` - `DSP010`: Dispute synchronization, reason parsing, and merchant record matching.
- `DSP011` - `DSP013`: Economic Net Expected Recovery calculation and Seller Protection rules.
- `DSP014` - `DSP017`: PayPal API execution (evidence submission, claim acceptance, message dispatch).
- `DSP018` - `DSP020`: Human-in-the-loop approval gate and deadline expiration.
- `DSP021` - `DSP025`: Security, PCI DSS sanitization, and audit reporting.
