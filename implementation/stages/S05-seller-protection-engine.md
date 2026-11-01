# S05 Seller Protection Rule Engine

## 1 Goal and outcome
Implement deterministic policy rules in `app/domain/seller_protection.py` for Item Not Received (`DSP007`), Unauthorised Transactions (`DSP008`), and Not As Described disputes (`DSP009`), returning eligibility tier and win probability estimate.

## 2 Entry conditions
- Stage S04 complete (Walking skeleton operational).

## 3 Read first
1. `catalog/DSP007.yaml`, `catalog/DSP008.yaml`, `catalog/DSP009.yaml`
2. `docs/SPEC.md` §3
3. `implementation/assets/reference/SELLER_PROTECTION_MATRIX.md`
4. `implementation/tests/S05-tests.md`

## 4 Files to create or modify
- `app/domain/seller_protection.py`
- `tests/unit/test_seller_protection.py`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- No network I/O or database access inside `app/domain/`.

## 6 Interfaces and signatures
```python
from app.domain.models import (
    ProtectionEligibility,
    DisputeReason,
    MerchantOrderRecord,
    DisputeRecord
)

class ProtectionEvaluationResult:
    eligibility: ProtectionEligibility
    win_probability: float
    evidence_type: str
    reasons: list[str]

class SellerProtectionEngine:
    @staticmethod
    def evaluate(dispute: DisputeRecord, order: MerchantOrderRecord) -> ProtectionEvaluationResult: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP007` | `catalog/fixtures/DSP007/` | Verify carrier tracking DELIVERED to recipient postal code; mark ELIGIBLE ($P_{\text{win}} \ge 0.90$) | Check status == "DELIVERED", postal code matches order shipping address, date prior to dispute | `applies_when`, `expected.outcome` |
| `DSP008` | `catalog/fixtures/DSP008/` | Verify shipment occurred prior to PayPal unauthorised notification date | Compare shipped_date < dispute.create_time; mark ELIGIBLE ($P_{\text{win}} \ge 0.85$) if true | `applies_when`, `correct_alternative` |
| `DSP009` | `catalog/fixtures/DSP009/` | Verify refund history or return policy acceptance for SNAD claims | Check refund_history for matching refund ID or return policy compliance | `applies_when`, `expected.outcome` |

## 8 Step-by-step instructions
1. Write tests in `tests/unit/test_seller_protection.py` per `S05-tests.md`. Verify they fail.
2. Implement `app/domain/seller_protection.py`:
   - Evaluate `MERCHANDISE_OR_SERVICE_NOT_RECEIVED`: check carrier `delivery_status == "DELIVERED"`, compare shipping address postal code prefix, assign `ELIGIBLE` and $P_{\text{win}} = 0.92$. If `IN_TRANSIT`, assign `PARTIALLY_ELIGIBLE` ($P_{\text{win}} = 0.60$).
   - Evaluate `UNAUTHORISED`: parse `shipped_date` and dispute `create_time`. If shipped prior to notification, assign `ELIGIBLE` and $P_{\text{win}} = 0.88$.
   - Evaluate `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED`: check `refund_history`. If prior full refund exists, assign `ELIGIBLE` ($P_{\text{win}} = 0.95$, evidence type `PROOF_OF_REFUND`).
3. Run tests until 100% green.

## 9 Edge cases
- ZIP+4 postal code matching (e.g. `90210-1234` matches `90210`).
- Carrier statuses formatted in lowercase normalized to uppercase.

## 10 Out of scope
- ROI expected value calculation (handled in S06).

## 11 Tests
Follow instructions in `implementation/tests/S05-tests.md`. Connect `DSP007`, `DSP008`, `DSP009` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Unit tests in `test_seller_protection.py` pass 100%.
- Catalog fixtures `DSP007`, `DSP008`, `DSP009` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(rules): implement seller protection policy engine for inr, unauthorised, and snad disputes (DSP007-DSP009)`

## 14 Failure and rollback handling
If address matching fails, verify postal code extraction strips spaces and hyphens before comparison.

## 15 Handoff notes for the next stage
Provides $P_{\text{win}}$ and eligibility inputs for S06 (Economic Decision Engine).
