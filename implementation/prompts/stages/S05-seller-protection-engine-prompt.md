ROLE: Rule engine specialist implementing PayPal Seller Protection policies for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S05 (Seller Protection Rule Engine) of DisputeSentry AI.
- Source of truth: `implementation/stages/S05-seller-protection-engine.md`
- Test instructions: `implementation/tests/S05-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP007`, `DSP008`, `DSP009`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S05-seller-protection-engine.md`, and `implementation/tests/S05-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S04 as `review-pass`.
4. Verify catalog fixtures for `DSP007`, `DSP008`, and `DSP009` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S05-seller-protection-engine.md` (`app/domain/seller_protection.py`, `tests/unit/test_seller_protection.py`).
- Strictly forbidden: Never perform network calls or database operations in `app/domain/`. Never edit `catalog/` or `docs/`.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S05-seller-protection-engine.md`.
2. Write unit tests first in `tests/unit/test_seller_protection.py` per `S05-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement pure deterministic functions in `app/domain/seller_protection.py`:
   - INR delivery verification and postal code matching (`DSP007`).
   - Unauthorised dispute shipment date check prior to notification (`DSP008`).
   - SNAD refund history and return policy matching (`DSP009`).
5. Connect `DSP007`, `DSP008`, `DSP009` to `tests/test_catalog_fixtures.py`.
6. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S05-seller-protection-engine.md`:
```bash
pytest tests/unit/test_seller_protection.py
pytest tests/test_catalog_fixtures.py -k "DSP007 or DSP008 or DSP009"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify all three catalog items pass.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S05 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(rules): implement seller protection policy engine for inr, unauthorised, and snad disputes (DSP007-DSP009)`

STOP CONDITIONS:
Stop immediately if postal code normalization or date comparison logic contradicts `SELLER_PROTECTION_MATRIX.md`. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S06`).
