# S07 tests: Human-in-the-Loop Approval Gate & Safe Fallbacks

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T07-01` | High-value dispute approval lock (`DSP013`) | Dispute amount $\$120.00$ ($> \$100.00$), action `CONTEST` | State is `PENDING_APPROVAL`, background worker skips auto-dispatch |
| `T07-02` | Low-value dispute auto-readiness | Dispute amount $\$45.00$ ($< \$100.00$), high confidence | State is `AUTO_READY`, auto-dispatched to PayPal client |
| `T07-03` | Concession action requires approval (`DSP015`) | Dispute amount $\$30.00$, action `CONCEDE` | State is `PENDING_APPROVAL` (all concessions require human sign-off) |
| `T07-04` | Operator approve API execution | Operator calls `POST /api/disputes/{id}/approve` | State transitions `PENDING_APPROVAL -> APPROVED -> DISPATCHED` |
| `T07-05` | 2-hour deadline fail-safe trigger (`DSP018`) | Dispute in `PENDING_APPROVAL` with `hours_until_due == 1.8` | Daemon triggers emergency evidence upload, transitions to `DISPATCHED`, logs warning |

## Positive cases
- Operator approval releases locked state and dispatches PayPal API call.
- Operator rejection halts action and marks dispute `REJECTED`.

## Negative cases
- Attempting to approve non-existent dispute returns 404 Not Found.
- Attempting to approve already `DISPATCHED` dispute raises `InvalidStateTransitionError`.

## Boundary cases
- Dispute amount exactly $\$100.00$ requires approval.
- Due date exactly $2.00\text{ hours}$ remaining activates emergency fallback.

## Fixtures and golden files used
- `catalog/fixtures/DSP013/`
- `catalog/fixtures/DSP015/`
- `catalog/fixtures/DSP018/`

## Commands to run (exact)
```bash
pytest tests/integration/test_approval_gate.py tests/unit/test_deadline_monitor.py -v
```

## Coverage target
- 95%+ coverage across `app/services/approval_gate.py` and `app/services/deadline_monitor.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Allowing automated workers to bypass approval on high-value disputes when confidence is high.
- Race conditions between operator clicking approve and the 2-hour fallback daemon firing.
