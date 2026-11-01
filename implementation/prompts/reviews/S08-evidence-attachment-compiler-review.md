ROLE: Independent auditor for stage S08 (Evidence Attachment Compiler & Validation) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S08-evidence-attachment-compiler.md`, `implementation/tests/S08-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S08-evidence-attachment-compiler.md` (`app/services/evidence_compiler.py`, `tests/unit/test_evidence_compiler.py`).
3. Tests: confirm tests in `tests/unit/test_evidence_compiler.py` cover all cases in `S08-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_evidence_compiler.py
   pytest tests/test_catalog_fixtures.py -k "DSP016 or DSP017"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare compilation and boundary encoding against `implementation/assets/flows/EVIDENCE_COMPILATION_FLOW.md`.
6. Quality: verify magic byte checking for JPG, PNG, GIF, and PDF. Verify strict rejection of single files $> 10\text{ MB}$ and total payloads $> 50\text{ MB}$.
7. Catalog items audit: re-verify `DSP016` (size constraints) and `DSP017` (MIME validation) against catalog specifications and oracle expectations.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
