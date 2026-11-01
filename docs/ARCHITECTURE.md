# Architecture Specification

## 1. System Overview and Component Diagram

DisputeSentry AI is designed as a modular, event-driven service implemented in Python 3.11+ using FastAPI, Pydantic v2, and SQLite 3.

```
+-----------------------------------------------------------------------------------+
|                              EXTERNAL BOUNDARY                                    |
|                                                                                   |
|   +-----------------------+              +------------------------------------+   |
|   | PayPal Webhook Engine |              | PayPal Disputes REST API v1        |   |
|   +-----------+-----------+              +-----------------+------------------+   |
+---------------|--------------------------------------------|----------------------+
                | POST /webhooks/paypal                      | GET/POST
                v                                            v
+-----------------------------------------------------------------------------------+
| APPLICATION CORE                                                                  |
|                                                                                   |
|  +---------------------------+            +------------------------------------+  |
|  | Webhook Ingestion Engine  |            | PayPal REST Client                 |  |
|  |  - Signature verifier     |            |  - OAuth 2.0 token cache           |  |
|  |  - Dedup filter           |            |  - Disputes fetcher & link checker |  |
|  +-------------+-------------+            |  - Multipart evidence submitter    |  |
|                |                          +-----------------+------------------+  |
|                v                                            ^                     |
|  +----------------------------------------------------------+------------------+  |
|  | Dispute Orchestrator Service                                                |  |
|  |  - Manages dispute lifecycle state machine                                  |  |
|  |  - Fetches external dispute & coordinates internal record lookup            |  |
|  +-------------+--------------------------------------------+------------------+  |
|                |                                            |                     |
|                v                                            v                     |
|  +---------------------------+            +------------------------------------+  |
|  | Merchant Data Repository  |            | Decision & ROI Reasoning Engine    |  |
|  |  - Orders store           |            |  - Seller Protection rules engine  |  |
|  |  - Shipments & Tracking   |            |  - Net Expected Recovery model     |  |
|  |  - Customer Comms         |            |  - AI structured reasoning         |  |
|  +-------------+-------------+            +-----------------+------------------+  |
|                |                                            |                     |
|                +---------------------+----------------------+                     |
|                                      |                                            |
|                                      v                                            |
|  +-----------------------------------------------------------------------------+  |
|  | Human-in-the-Loop Approval Gate & Queue                                      |  |
|  |  - Auto-execution router (< $100 & high confidence)                         |  |
|  |  - Pending operator review queue (>= $100 or low confidence)                |  |
|  |  - Response deadline countdown & safety fallback                            |  |
|  +-----------------------------------+-----------------------------------------+  |
|                                      |                                            |
|                                      v                                            |
|  +---------------------------+            +------------------------------------+  |
|  | Storage & Audit Layer     |            | Web Dashboard & Operator UI        |  |
|  |  - SQLite (WAL mode)      |            |  - Real-time priority queue view   |  |
|  |  - Immutable audit trail  |            |  - Action approval controls        |  |
|  |  - State hash computation |            |  - Win rate & recovery analytics   |  |
|  +---------------------------+            +------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

---

## 2. Package and Module Boundaries

The codebase follows clean architecture principles with strict dependency direction:

```
app/
├── main.py                     # Application entry point & FastAPI factory
├── config.py                   # Pydantic-settings environment configuration
├── domain/                     # Core domain models and business rules (Zero I/O)
│   ├── models.py               # Dispute, EvidencePackage, DecisionResult, State
│   ├── seller_protection.py    # Deterministic PayPal Seller Protection logic
│   ├── economics.py            # Net Expected Recovery ROI calculation
│   └── sanitizer.py            # PCI DSS PAN and CVV scrubbing & prompt shielding
├── services/                   # Application orchestration and business use cases
│   ├── orchestrator.py         # Dispute lifecycle state machine coordinator
│   ├── decision_engine.py      # Combines deterministic rules with AI reasoning
│   ├── approval_gate.py        # Human approval management and deadline monitor
│   └── audit_service.py        # Tamper-evident audit log writer
├── clients/                    # External infrastructure adapters (I/O)
│   ├── paypal_client.py        # PayPal Disputes REST API v1 & OAuth2 token client
│   ├── webhook_verifier.py     # PayPal X.509 cert and RSA-SHA256 signature verifier
│   └── ai_client.py            # Google Gemini structured output adapter
├── storage/                    # Database repositories & schema migrations
│   ├── database.py             # SQLite connection management & WAL configuration
│   ├── dispute_repo.py         # Dispute state persistence
│   ├── merchant_repo.py        # Seeded merchant orders and shipment records
│   └── audit_repo.py           # Append-only audit log storage
└── ui/                         # Web presentation layer
    ├── routes.py               # REST API & HTML dashboard endpoints
    └── templates/              # Jinja2 responsive UI templates
```

---

## 3. Data Flow and State Machine

A dispute transitions through a formal Finite State Machine (FSM):

```
       +-----------------------+
       |       RECEIVED        |  (Webhook ingested & validated)
       +-----------+-----------+
                   |
                   v
       +-----------------------+
       |       EVALUATING      |  (Records matched & ROI calculated)
       +-----------+-----------+
                   |
         +---------+---------+
         |                   |
 [Auto-Eligible]     [Requires Approval]
         |                   |
         v                   v
+-----------------+ +-------------------+
|  AUTO_EXECUTING | | PENDING_APPROVAL  | <---+ (Awaiting operator review)
+--------+--------+ +---------+---------+     |
         |                    |               |
         |            +-------+-------+       |
         |            |               |       |
         |       [Approved]      [Rejected]   |
         |            |               |       |
         v            v               v       |
+---------------------------------------+     |
|           SUBMITTING_ACTION           |     |
| (Calls provide-evidence / accept-claim)|    |
+-------------------+-------------------+     |
                    |                         |
          +---------+---------+               |
          |                   |               |
      [Success]            [Error]            |
          |                   |               |
          v                   v               |
+-------------------+ +-------------------+   |
|     SUBMITTED     | | SUBMISSION_FAILED | --+ (Retry or escalate)
+---------+---------+ +-------------------+
          |
          v (Upon CUSTOMER.DISPUTE.RESOLVED)
+-------------------+
|     RESOLVED      |
+-------------------+
```

---

## 4. Mapping Catalog Items to Code

Every catalog item (`DSP###`) maps directly to an explicit code component and test suite:

| Catalog Range | Domain Topic | Implementation Module | Automated Test File |
|---|---|---|---|
| `DSP001` - `DSP004` | Webhook verification & security | `app/clients/webhook_verifier.py` | `tests/test_webhook_verifier.py` |
| `DSP005`, `DSP014`, `DSP015` | PayPal API execution & contracts | `app/clients/paypal_client.py` | `tests/test_paypal_client.py` |
| `DSP006` | Merchant record lookup | `app/storage/merchant_repo.py` | `tests/test_merchant_repo.py` |
| `DSP007` - `DSP009` | Seller Protection rules | `app/domain/seller_protection.py` | `tests/test_seller_protection.py` |
| `DSP010`, `DSP018` | Deadlines & urgent alerts | `app/services/approval_gate.py` | `tests/test_deadline_safeguards.py` |
| `DSP011` | ROI & Net Expected Recovery | `app/domain/economics.py` | `tests/test_economics.py` |
| `DSP012` | Inquiry stage messaging | `app/services/orchestrator.py` | `tests/test_orchestrator.py` |
| `DSP013` | Human approval gate | `app/services/approval_gate.py` | `tests/test_approval_gate.py` |
| `DSP016`, `DSP017` | Evidence file constraints | `app/domain/models.py` | `tests/test_file_constraints.py` |
| `DSP019` | PCI DSS PAN scrubbing | `app/domain/sanitizer.py` | `tests/test_sanitizer.py` |
| `DSP020` | Prompt injection isolation | `app/clients/ai_client.py` | `tests/test_ai_shielding.py` |
| `DSP021` | Win rate & net recovery metrics | `app/services/audit_service.py` | `tests/test_metrics.py` |
| `DSP022` | Tamper-evident audit logging | `app/storage/audit_repo.py` | `tests/test_audit_trail.py` |

---

## 5. Error Handling and Resilience Strategy

1. **Transient Network Failures**:
   - Outbound HTTP calls to PayPal Sandbox API utilize exponential backoff retry logic (up to 3 retries for HTTP 500, 502, 503, 504 and network disconnects).
2. **Expired OAuth Tokens**:
   - The PayPal client intercepts HTTP 401 Unauthorized responses, purges the in-memory token cache, retrieves a fresh bearer token, and replays the original request automatically.
3. **Database Concurrency**:
   - SQLite Write-Ahead Logging (`WAL` mode) allows concurrent readers to query the dashboard and metrics without blocking background webhook writes.
