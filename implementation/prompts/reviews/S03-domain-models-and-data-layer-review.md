ROLE: Independent auditor for stage S03 (Domain Models, PCI Sanitization & Audit Store) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S03-domain-models-and-data-layer.md`, `implementation/tests/S03-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S03-domain-models-and-data-layer.md`.
3. Tests: confirm tests in `tests/unit/test_sanitizer.py`, `tests/unit/test_audit_service.py`, and `tests/integration/test_storage.py` cover all cases in `S03-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_sanitizer.py tests/unit/test_audit_service.py tests/integration/test_storage.py
   pytest tests/test_catalog_fixtures.py -k "DSP006 or DSP019 or DSP022"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare domain models against `implementation/assets/data-models/CORE_TYPES.md`.
6. Quality: audit `app/services/sanitizer.py` for correct Luhn validation. Confirm zero raw PANs persisted. Verify audit trail hashes chain sequentially (`prev_hash` to `entry_hash`).
7. Catalog items audit: re-verify `DSP019` (cardholder scrubbing) and `DSP022` (tamper-evident audit store) against catalog specifications and oracle expectations; confirm code matches catalog requirements.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
