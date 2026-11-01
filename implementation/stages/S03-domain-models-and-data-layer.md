# S03 Domain Models, PCI Sanitization & Audit Store

## 1 Goal and outcome
Establish the SQLite 3 WAL database layer, core Pydantic domain models (`DisputeRecord`, `MerchantOrderRecord`, `AuditTrailEntry`), seeded merchant orders, the PCI DSS cardholder data/CVV scrubber (`DSP019`), and the SHA-256 chained tamper-evident audit trail (`DSP022`).

## 2 Entry conditions
- Stage S02 complete (`DSP001` - `DSP004` passing).
- `aiosqlite` installed and importable.

## 3 Read first
1. `catalog/DSP006.yaml`, `catalog/DSP019.yaml`, `catalog/DSP022.yaml`
2. `implementation/assets/data-models/CORE_TYPES.md`
3. `implementation/assets/architecture/CODING_STANDARDS.md` §3
4. `implementation/tests/S03-tests.md`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- Never store raw unmasked PAN or CVV in SQLite or log output.
- Never allow updating or deleting historical rows in the audit trail table.

## 6 Interfaces and signatures
```python
from typing import Any
from app.domain.models import DisputeRecord, MerchantOrderRecord, AuditTrailEntry

class PCISanitizer:
    @staticmethod
    def sanitize(text: str) -> str: ...
    @staticmethod
    def contains_pan(text: str) -> bool: ...

class AuditService:
    def __init__(self, db_conn: Any): ...
    async def log_action(self, dispute_id: str, action: str, actor: str, details: dict) -> AuditTrailEntry: ...
    async def verify_chain_integrity(self, dispute_id: str) -> bool: ...

class MerchantRepository:
    async def get_order_by_transaction(self, tx_id: str) -> MerchantOrderRecord | None: ...
    async def save_dispute(self, dispute: DisputeRecord) -> None: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP006` | `catalog/fixtures/DSP006/` | Return matched merchant order, tracking, delivery status | Query SQLite database on transaction_id/invoice_id; return structured record | `applies_when`, `expected.outcome` |
| `DSP019` | `catalog/fixtures/DSP019/` | Scrub 13-19 digit card numbers (Luhn-valid) and CVVs from text | Mask card numbers preserving first 4 and last 4; replace CVV with [REDACTED] | `applies_when`, `correct_alternative` |
| `DSP022` | `catalog/fixtures/DSP022/` | Append-only audit entry cryptographically linked with SHA-256 | Compute entry_hash = SHA256(data + prev_hash); verify chain detects alterations | `applies_when`, `expected.outcome` |

## 8 Step-by-step instructions
1. Write tests in `tests/unit/test_sanitizer.py`, `tests/unit/test_audit_service.py`, `tests/integration/test_storage.py` per `S03-tests.md`. Verify they fail.
2. Implement `app/domain/models.py` with `DisputeRecord`, `Money`, `MerchantOrderRecord`, `AuditTrailEntry` per `CORE_TYPES.md`.
3. Implement `app/services/sanitizer.py`:
   - Regex scan for candidate 13-19 digit patterns; evaluate Luhn checksum.
   - If Luhn-valid, mask middle digits: `4111-XXXX-XXXX-1111`.
   - Regex scan for CVV patterns (`(?i)cvv\s*[:=]?\s*\d{3,4}`); replace with `[REDACTED]`.
4. Implement `app/storage/database.py` with async table creation (WAL mode).
5. Implement `app/storage/seed_data.py` inserting fixture orders (`ORD-1001`, `ORD-1002`, `ORD-1003`).
6. Implement `app/storage/repository.py` for dispute and order operations.
7. Implement `app/services/audit_service.py`:
   - Fetch last `entry_hash` for dispute (or 64 zeros for initial).
   - Format entry payload, compute `entry_hash = SHA256(canonical_json(data) + prev_hash)`.
   - Insert row append-only.
   - Implement `verify_chain_integrity(dispute_id)`.
8. Run tests until 100% green.

## 9 Edge cases
- Consecutive card numbers separated by commas or punctuation.
- First audit entry for a dispute uses `0` * 64 as `prev_hash`.

## 10 Out of scope
- PayPal client API integration (handled in S04).
- Rule engine logic (handled in S05).

## 11 Tests
Follow instructions in `implementation/tests/S03-tests.md`. Connect `DSP006`, `DSP019`, `DSP022` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Unit and integration tests pass 100%.
- Catalog fixtures `DSP006`, `DSP019`, `DSP022` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(storage): implement domain models, seeded order store, pci sanitizer, and chained audit trail (DSP006, DSP019, DSP022)`

## 14 Failure and rollback handling
If audit integrity check fails, verify canonical JSON serialization uses sorted keys to prevent dict order hashing discrepancies.

## 15 Handoff notes for the next stage
Provides seeded merchant database and audit store for S04 (Walking Skeleton).
