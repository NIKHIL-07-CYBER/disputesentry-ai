# Verification Protocol

This document defines the automated verification protocol used to validate DisputeSentry AI against the ground truth definitions established in [ADR-004](file:///D:/fix/challenges/paypal/docs/adr/ADR-004-verification-strategy.md).

---

## 1. Ground Truth Verification Architecture

```
                       +---------------------------------------+
                       | Catalog Items (DSP001 - DSP022)       |
                       +-------------------+-------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| Offline Deterministic Test Suite (pytest)                                         |
|  - In-memory SQLite fixture databases                                             |
|  - Mocked PayPal Disputes API v1 responses (respx / contract mocks)               |
|  - Fixed cryptographic keypairs for PayPal webhook signature verification         |
|  - Zero network dependencies; executes in < 3 seconds                             |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| Live PayPal Sandbox Verification Suite                                            |
|  - OAuth 2.0 client credentials token acquisition                                 |
|  - Dispute retrieval from https://api-m.sandbox.paypal.com                        |
|  - Synthetic dispute state updates & multipart evidence upload                    |
|  - Rate-limit backoff and retry handling                                          |
+-----------------------------------------------------------------------------------+
```

---

## 2. Test Execution Environments and Matrix

| Environment Tier | Target | Frequency | Network Dependency |
|---|---|---|---|
| **Tier 1: Fixture Validation** | All `catalog/fixtures/DSP###/` inputs vs `expected.yaml` | Pre-commit & CI | None (Offline) |
| **Tier 2: Unit & State Machine** | Pydantic schema validation, ROI economics, PCI redaction, approval FSM | Every build | None (Offline) |
| **Tier 3: Mock Contract Tests** | PayPal Disputes API v1 mock endpoints (200, 400, 401, 409, 413) | Every build | None (Local `respx`) |
| **Tier 4: Live Sandbox E2E** | Live PayPal Sandbox environment (`api-m.sandbox.paypal.com`) | Milestone verification | Active Internet & Sandbox credentials |

---

## 3. Fixture Runner Protocol

The test runner iterates through all catalog fixtures in `catalog/fixtures/DSP###/` and executes the following verification sequence:

1. **Setup**:
   - Initialize an isolated SQLite database in temporary memory (`:memory:`).
   - Load seed schema and baseline test records.
   - For cryptographic tests (`DSP001` - `DSP004`), load a pre-generated 2048-bit RSA test certificate.
2. **Execution**:
   - Dispatch `good.json` to the target component; record output response.
   - Dispatch `bad.json` to the target component; record error response and status.
3. **Assertion**:
   - Compare observed outputs against `expected.yaml`.
   - Assert exact match on status codes, error codes, and field values.
4. **Teardown**:
   - Close in-memory database connections and purge temporary mock caches.

---

## 4. Promotion Policy: Moving from `docs-cited` to `test-verified`

Every catalog item begins with `verification_status: docs-cited`. An item is promoted to `test-verified` only when:
1. Its fixture files (`good.json`, `bad.json`, `expected.yaml`) exist and pass the Tier 1 fixture test runner.
2. An automated integration test executes the behavior against either:
   - The deterministic offline mock suite with 100% assertions green, OR
   - The live PayPal Sandbox API with a confirmed 200 OK response.
3. The test execution log is recorded with test timestamp and commit hash.

---

## 5. Avoiding Test Flakiness and Timeouts

To prevent test flakiness in automated testing:
1. **Clock Isolation**:
   - Tests evaluating `seller_response_due_date` (`DSP010`, `DSP018`) must never rely on system wall clock time (`datetime.now()`). Use dependency injection for the clock provider (e.g., `freezegun` or an explicit `now_fn` parameter).
2. **PayPal Sandbox Rate Limits**:
   - When running Tier 4 live sandbox tests, queries to `api-m.sandbox.paypal.com` must implement exponential backoff with jitter (initial delay 500 ms, multiplier 2.0, max 3 retries).
3. **Database Concurrency Isolation**:
   - Each test test case uses an isolated database connection or temporary directory database file to prevent lock contention.

---

## 6. Pass/Fail Criteria Checklist

- [ ] 100% of catalog items (`DSP001` - `DSP022`) have valid `good.json`, `bad.json`, and `expected.yaml`.
- [ ] Tier 1 fixture suite passes with 0 failures and 0 warnings.
- [ ] Tier 2 unit test suite passes with 100% coverage on core financial and Seller Protection algorithms.
- [ ] PCI DSS sanitizer (`DSP019`) detects and redacts 100% of test card numbers with zero leaks.
- [ ] Prompt injection benchmark (`DSP020`) successfully suppresses 100% of adversarial instruction attempts.
- [ ] Live sandbox run successfully ingests a test dispute and submits a test evidence payload without unhandled exceptions.
