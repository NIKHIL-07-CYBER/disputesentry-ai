ROLE: Database and security engineer implementing data models, PCI sanitization, and audit store for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S03 (Domain Models, PCI Sanitization & Audit Store) of DisputeSentry AI.
- Source of truth: `implementation/stages/S03-domain-models-and-data-layer.md`
- Test instructions: `implementation/tests/S03-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP006`, `DSP019`, `DSP022`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S03-domain-models-and-data-layer.md`, and `implementation/tests/S03-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S02 as `review-pass`.
4. Verify catalog fixtures for `DSP006`, `DSP019`, and `DSP022` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S03-domain-models-and-data-layer.md` (`app/models/`, `app/domain/models.py`, `app/storage/`, `app/services/sanitizer.py`, `app/services/audit_service.py`, test files).
- Strictly forbidden: Never edit `catalog/` or `docs/`. Never persist raw cardholder numbers or CVVs.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S03-domain-models-and-data-layer.md`.
2. Write tests first in `tests/unit/test_sanitizer.py`, `tests/unit/test_audit_service.py`, and `tests/integration/test_storage.py` per `S03-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/domain/models.py` per `CORE_TYPES.md`.
5. Implement `app/services/sanitizer.py` (Luhn algorithm, PAN masking, CVV removal).
6. Implement `app/storage/database.py`, `app/storage/seed_data.py`, `app/storage/repository.py`, and `app/services/audit_service.py` (SHA-256 hash chaining).
7. Connect `DSP006`, `DSP019`, `DSP022` to `tests/test_catalog_fixtures.py`.
8. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S03-domain-models-and-data-layer.md`:
```bash
pytest tests/unit/test_sanitizer.py tests/unit/test_audit_service.py tests/integration/test_storage.py
pytest tests/test_catalog_fixtures.py -k "DSP006 or DSP019 or DSP022"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify zero PAN leaks and hash chain verification succeeds.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S03 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(storage): implement domain models, seeded order store, pci sanitizer, and chained audit trail (DSP006, DSP019, DSP022)`

STOP CONDITIONS:
Stop immediately if audit trail hash calculation produces discrepancies or Luhn sanitizer masks non-card data.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S04`).
