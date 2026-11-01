# S04 tests: Walking Skeleton: PayPal Client & Dispute Sync

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T04-01` | OAuth2 token acquisition & cache | `POST /v1/oauth2/token` via `respx` mock | Acquires token `access_token_123`, caches until `expires_in`, refreshes automatically |
| `T04-02` | HATEOAS link validation (`DSP005`) | Dispute payload with `links: [{"rel": "accept_claim", ...}]` (missing `provide_evidence`) | Calling `provide_evidence()` raises `HATEOASViolationError("Action 'provide_evidence' not permitted")` |
| `T04-03` | Response due date calculation (`DSP010`) | Ingest dispute with `seller_response_due_date` set to $T + 36\text{ hours}$ | `hours_until_due == 36.0`, `urgency_tier == "MEDIUM"` |
| `T04-04` | Provide-evidence API submission (`DSP014`) | Valid tracking package submitted for `PP-D-12345` | `respx` captures POST `/v1/customer/disputes/PP-D-12345/provide-evidence`; returns HTTP 200 |
| `T04-05` | Walking skeleton end-to-end slice | Send valid webhook -> order lookup -> deadline calc -> dispatch evidence | Complete pipeline executes; database records state `DISPATCHED` |

## Positive cases
- Token refresh handles 401 response and retries request with new token.
- Valid `provide_evidence` link permits dispatch and records evidence in audit log.

## Negative cases
- Missing required link returns 409 Conflict domain error.
- Expired deadline triggers `DisputeExpiredError`.

## Boundary cases
- Due date precisely at threshold boundary ($24.0\text{ hours}$, $72.0\text{ hours}$).

## Fixtures and golden files used
- `catalog/fixtures/DSP005/`
- `catalog/fixtures/DSP010/`
- `catalog/fixtures/DSP014/`

## Commands to run (exact)
```bash
pytest tests/contract/test_paypal_client.py tests/integration/test_dispute_sync.py -v
```

## Coverage target
- 90%+ coverage across `app/clients/paypal_client.py` and `app/services/dispute_sync.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Hardcoding bearer token strings.
- Proceeding with evidence upload when PayPal dispute stage is already `RESOLVED`.
