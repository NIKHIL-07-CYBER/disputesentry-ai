# S07 Human-in-the-Loop Approval Gate & Safe Fallbacks

## 1 Goal and outcome
Implement the human oversight state machine in `app/services/approval_gate.py` locking disputes $\ge \$100$ or concessions (`DSP013`), the concession execution worker calling PayPal `accept-claim` (`DSP015`), and the 2-hour deadline fail-safe background daemon (`DSP018`).

## 2 Entry conditions
- Stage S06 complete (`DSP011`, `DSP012`, `DSP021` passing).

## 3 Read first
1. `catalog/DSP013.yaml`, `catalog/DSP015.yaml`, `catalog/DSP018.yaml`
2. `docs/SPEC.md` §4.2.2
3. `implementation/assets/flows/APPROVAL_GATE_FLOW.md`
4. `implementation/tests/S07-tests.md`

## 4 Files to create or modify
- `app/services/approval_gate.py`
- `app/services/deadline_monitor.py`
- `app/api/approvals.py`
- `tests/integration/test_approval_gate.py`
- `tests/unit/test_deadline_monitor.py`

## 5 Forbidden changes
- Never auto-execute concessions or actions on disputes $\ge \$100$ without operator approval (unless deadline fallback triggers).
- Never allow approving an already dispatched or resolved dispute.

## 6 Interfaces and signatures
```python
from app.domain.models import DisputeRecord, InternalState

class ApprovalGateService:
    def __init__(self, repo: MerchantRepository, client: PayPalDisputesClient, audit: AuditService): ...
    async def evaluate_gate(self, dispute: DisputeRecord) -> InternalState: ...
    async def approve_dispute(self, dispute_id: str, operator_id: str) -> DisputeRecord: ...
    async def reject_dispute(self, dispute_id: str, operator_id: str) -> DisputeRecord: ...

class DeadlineMonitorDaemon:
    async def check_expiring_disputes(self) -> list[str]: ...
    async def trigger_fail_safe(self, dispute_id: str) -> None: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP013` | `catalog/fixtures/DSP013/` | Intercept disputes >= $100 into PENDING_APPROVAL; prevent automated mutation | If dispute_amount >= 100.0, set internal_state = PENDING_APPROVAL and lock | `applies_when`, `expected.outcome` |
| `DSP015` | `catalog/fixtures/DSP015/` | Execute accept-claim API concession only after operator signs off | POST /v1/customer/disputes/{id}/accept-claim; transition to RESOLVED | `applies_when`, `correct_alternative` |
| `DSP018` | `catalog/fixtures/DSP018/` | Trigger automatic evidence submission if time <= 2 hours to avoid default forfeit | If hours_until_due <= 2.0 and state == PENDING_APPROVAL, auto-dispatch | `applies_when`, `expected.outcome` |

## 8 Step-by-step instructions
1. Write tests in `tests/integration/test_approval_gate.py` and `tests/unit/test_deadline_monitor.py` per `S07-tests.md`. Verify they fail.
2. Implement `app/services/approval_gate.py`:
   - Evaluate dispute amount: if $\ge \$100.00$ or action is `CONCEDE`, state becomes `PENDING_APPROVAL`.
   - If amount $< \$100.00$ and action is `CONTEST` and confidence high, state becomes `AUTO_READY`.
   - Implement `approve_dispute`: transition state `PENDING_APPROVAL -> APPROVED -> DISPATCHED`.
   - Implement `reject_dispute`: transition state `PENDING_APPROVAL -> REJECTED`.
3. Implement `app/api/approvals.py` routes:
   - `POST /api/disputes/{id}/approve`
   - `POST /api/disputes/{id}/reject`
4. Implement `app/services/deadline_monitor.py`:
   - Scan disputes in `PENDING_APPROVAL` with `hours_until_due <= 2.0`.
   - Invoke `trigger_fail_safe`: log audit alert, execute defensive evidence submission, update state to `DISPATCHED`.
5. Run tests until 100% green.

## 9 Edge cases
- Dispute amount precisely $\$100.00$ triggers approval lock.
- Deadline monitor race condition with operator approval handled atomically via SQLite transaction lock.

## 10 Out of scope
- File attachment multipart compilation (handled in S08).

## 11 Tests
Follow instructions in `implementation/tests/S07-tests.md`. Connect `DSP013`, `DSP015`, `DSP018` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Approval gate tests pass 100%.
- Catalog fixtures `DSP013`, `DSP015`, `DSP018` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(oversight): implement human approval gate, concession executor, and 2-hour deadline fail-safe (DSP013, DSP015, DSP018)`

## 14 Failure and rollback handling
If approval transitions fail, check that SQLite updates enforce row versioning or transactional concurrency guards.

## 15 Handoff notes for the next stage
Provides safe dispatch boundaries for S08 (Evidence Attachment Compiler).
