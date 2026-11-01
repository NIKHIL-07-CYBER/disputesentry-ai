# Performance Budget and Latency Allocations

DisputeSentry AI must process high-priority webhooks, evaluate disputes against deadlines, and serve merchant dashboard interactions within strict timing constraints.

---

## 1. Latency Budgets

| Operation | Budget Ceiling | Target (p95) | Rationale |
|---|---|---|---|
| **Webhook Ingestion (`POST /webhooks/paypal`)** | `< 250 ms` | `< 80 ms` | PayPal webhook delivery endpoints timeout after 30 seconds, but quick 200 OK prevents unnecessary upstream retries and queue buildup. |
| **Cryptographic Signature Verification** | `< 50 ms` | `< 15 ms` | In-memory public key caching prevents repetitive X.509 cert downloads. |
| **Database Order & Record Lookup** | `< 20 ms` | `< 5 ms` | SQLite indexed lookup on `order_id` / `transaction_id`. |
| **Seller Protection Rule Evaluation** | `< 10 ms` | `< 2 ms` | In-memory deterministic rule matching. |
| **Economic Expected Value (ROI) Calc** | `< 5 ms` | `< 1 ms` | Pure mathematical floating-point calculation. |
| **AI Structured Reasoning Call** | `< 4000 ms` | `< 1800 ms` | External Gemini 1.5/2.5 Flash invocation with structured JSON response. |
| **Evidence Attachment Compilation (50MB max)** | `< 500 ms` | `< 150 ms` | In-memory validation and boundary encoding. |
| **Dashboard Page Load (`GET /dashboard`)** | `< 100 ms` | `< 35 ms` | Server-rendered Jinja2 template with SQLite query. |

---

## 2. Resource Consumption Ceilings

- **Memory Usage:** `< 250 MB` RSS idle; `< 512 MB` under peak 50 MB multipart compilation.
- **Disk Space:** SQLite DB `< 50 MB` for 10,000 disputes + audit trail in WAL mode.
- **Test Suite Execution Time:** Full offline test suite (`pytest`) must complete in `< 5.0 seconds`.
