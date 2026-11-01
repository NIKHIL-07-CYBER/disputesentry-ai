ROLE: Independent auditor for stage S05 (Seller Protection Rule Engine) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S05-seller-protection-engine.md`, `implementation/tests/S05-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S05-seller-protection-engine.md` (`app/domain/seller_protection.py`, `tests/unit/test_seller_protection.py`).
3. Tests: confirm unit tests in `tests/unit/test_seller_protection.py` cover all cases in `S05-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_seller_protection.py
   pytest tests/test_catalog_fixtures.py -k "DSP007 or DSP008 or DSP009"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare rules against `implementation/assets/reference/SELLER_PROTECTION_MATRIX.md`. Confirm domain rules are 100% deterministic and free of network I/O or database queries.
6. Quality: check for edge-case coverage: postal code normalization, case-insensitive carrier status matching, and timestamp comparisons.
7. Catalog items audit: re-verify `DSP007` (INR delivery check) and `DSP008` (Unauthorised prior shipment check) against catalog specifications and oracle expectations.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
