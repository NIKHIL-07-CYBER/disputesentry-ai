# S03 tests: Domain Models, PCI Sanitization & Audit Store

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T03-01` | Merchant order lookup (`DSP006`) | Query `TX-1001` against seeded SQLite DB | Returns `MerchantOrderRecord(order_id="ORD-1001", carrier="USPS", tracking_number="9400100000000000000000")` |
| `T03-02` | PCI DSS cardholder scrubbing (`DSP019`) | String `"Buyer card: 4111 2222 3333 4444 CVV 123"` | Sanitized: `"Buyer card: 4111-XXXX-XXXX-4444 CVV [REDACTED]"` |
| `T03-03` | Tamper-evident audit trail chain (`DSP022`) | Append 3 sequential audit entries | Entry 2 `prev_hash` equals Entry 1 `entry_hash`; Entry 3 `prev_hash` equals Entry 2 `entry_hash` |
| `T03-04` | Audit trail tampering detection (`DSP022`) | Mutate action field in Entry 1 directly in database | `verify_audit_integrity()` returns `False` and flags Entry 1 as corrupted |

## Positive cases
- Seeded merchant database initializes and returns known orders by transaction ID and invoice number.
- Card numbers matching Luhn checksum are masked preserving first 4 and last 4 digits.
- 3 and 4 digit CVVs preceded by "CVV" or "CVC" are masked.

## Negative cases
- Unknown transaction ID returns `OrderNotFoundError`.
- Non-Luhn digit sequences (e.g., 16 random non-card digits) are left unmasked.

## Boundary cases
- Single character card delimiter variants (spaces, dashes, dots).
- Empty audit log returns `verify_audit_integrity() == True`.

## Fixtures and golden files used
- `catalog/fixtures/DSP006/`
- `catalog/fixtures/DSP019/`
- `catalog/fixtures/DSP022/`

## Commands to run (exact)
```bash
pytest tests/unit/test_sanitizer.py tests/unit/test_audit_service.py tests/integration/test_storage.py -v
```

## Coverage target
- 95%+ coverage across `app/services/sanitizer.py`, `app/services/audit_service.py`, `app/storage/repository.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Over-aggressive regex masking non-card numbers such as 16-digit order or tracking numbers.
- Failing to commit transaction in SQLite before verifying audit hash chain.
