# S04 Walking Skeleton: PayPal Client & Dispute Sync

## 1 Goal and outcome
Deliver an end-to-end working vertical slice: an authentic webhook triggers dispute synchronization, retrieves merchant fulfillment records, calculates deadline urgency (`DSP010`), validates allowed HATEOAS actions (`DSP005`), and dispatches provide-evidence payload to PayPal Disputes API v1 (`DSP014`) via async client.

## 2 Entry conditions
- Stage S03 complete (`DSP006`, `DSP019`, `DSP022` passing).
- `respx` mock router configured in test harness.

## 3 Read first
1. `catalog/DSP005.yaml`, `catalog/DSP010.yaml`, `catalog/DSP014.yaml`
2. `docs/SPEC.md` §4.2.3
3. `implementation/assets/flows/DISPUTE_SYNC_FLOW.md`
4. `implementation/assets/reference/PAYPAL_API_MATRIX.md`
5. `implementation/tests/S04-tests.md`

## 4 Files to create or modify
- `app/clients/paypal_client.py`
- `app/services/dispute_sync.py`
- `tests/contract/test_paypal_client.py`
- `tests/integration/test_dispute_sync.py`

## 5 Forbidden changes
- Never hardcode live PayPal credentials into code.
- Never bypass HATEOAS link validation.

## 6 Interfaces and signatures
```python
class PayPalDisputesClient:
    def __init__(self, client_id: str, client_secret: str, base_url: str): ...
    async def get_access_token(self) -> str: ...
    async def get_dispute(self, dispute_id: str) -> dict: ...
    async def provide_evidence(self, dispute_id: str, evidence_payload: dict) -> dict: ...

class DisputeSyncCoordinator:
    def __init__(self, client: PayPalDisputesClient, repo: MerchantRepository, audit: AuditService): ...
    async def handle_dispute_event(self, webhook_resource: dict) -> DisputeRecord: ...
    def compute_deadline_urgency(self, due_date_iso: str) -> tuple[float, str]: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP005` | `catalog/fixtures/DSP005/` | Validate HATEOAS link present before attempting mutation; raise error if missing | Inspect `links` array on dispute; reject `provide_evidence` call if link absent | `applies_when`, `correct_alternative` |
| `DSP010` | `catalog/fixtures/DSP010/` | Compute hours remaining until response due date; classify urgency tier | Parse `seller_response_due_date` against current UTC; assign LOW/MED/CRITICAL | `applies_when`, `expected.outcome` |
| `DSP014` | `catalog/fixtures/DSP014/` | Dispatch provide-evidence payload with carrier tracking to PayPal API | Submit POST to `/v1/customer/disputes/{id}/provide-evidence` with valid tracking info | `applies_when`, `expected.outcome` |

## 8 Step-by-step instructions
1. Write tests in `tests/contract/test_paypal_client.py` and `tests/integration/test_dispute_sync.py` per `S04-tests.md`. Verify they fail.
2. Implement `app/clients/paypal_client.py`:
   - Async OAuth 2.0 client credentials token flow with automatic caching until expiry.
   - Automatic 401 retry with token refresh.
   - `GET /v1/customer/disputes/{id}` and `POST /v1/customer/disputes/{id}/provide-evidence`.
3. Implement `app/services/dispute_sync.py`:
   - Ingest webhook resource, look up transaction in `MerchantRepository`.
   - Calculate `hours_until_due` from `seller_response_due_date`.
   - Validate that `links` contains `rel="provide_evidence"`. If missing, raise `HATEOASViolationError`.
   - Assemble tracking package and call `paypal_client.provide_evidence()`.
   - Record action in `AuditService`.
4. Run tests until 100% green.

## 9 Edge cases
- Expired OAuth token refreshed seamlessly mid-flight.
- Missing `seller_response_due_date` sets status to review required.

## 10 Out of scope
- Full Seller Protection rule engine (handled in S05).
- ROI calculation engine (handled in S06).

## 11 Tests
Follow instructions in `implementation/tests/S04-tests.md`. Connect `DSP005`, `DSP010`, `DSP014` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Contract tests and integration tests pass 100%.
- Walking skeleton end-to-end slice executes successfully.
- Catalog fixtures `DSP005`, `DSP010`, `DSP014` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(sync): implement paypal client, hateoas link check, deadline urgency, and walking skeleton (DSP005, DSP010, DSP014)`

## 14 Failure and rollback handling
If HATEOAS checks fail on valid mock disputes, ensure link `rel` names match both `provide_evidence` and `provide-evidence` variants.

## 15 Handoff notes for the next stage
Walking skeleton is proven. S05 expands domain intelligence with the Seller Protection Rule Engine.
