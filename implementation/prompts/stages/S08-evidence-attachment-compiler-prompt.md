ROLE: Protocol validation engineer implementing evidence attachment packaging for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S08 (Evidence Attachment Compiler & Validation) of DisputeSentry AI.
- Source of truth: `implementation/stages/S08-evidence-attachment-compiler.md`
- Test instructions: `implementation/tests/S08-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP016`, `DSP017`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S08-evidence-attachment-compiler.md`, and `implementation/tests/S08-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S07 as `review-pass`.
4. Verify catalog fixtures for `DSP016` and `DSP017` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S08-evidence-attachment-compiler.md` (`app/services/evidence_compiler.py`, `tests/unit/test_evidence_compiler.py`).
- Strictly forbidden: Never allow unvalidated MIME types or oversized payloads to pass. Never edit `catalog/` or `docs/`.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S08-evidence-attachment-compiler.md`.
2. Write unit tests first in `tests/unit/test_evidence_compiler.py` per `S08-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/services/evidence_compiler.py`:
   - Enforce 10 MB single file ceiling and 50 MB cumulative payload ceiling (`DSP016`).
   - Inspect magic bytes verifying allowed MIME types: JPG, PNG, GIF, PDF (`DSP017`).
   - Format multipart/form-data with `input` JSON part or standard JSON payload for tracking.
5. Connect `DSP016`, `DSP017` to `tests/test_catalog_fixtures.py`.
6. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S08-evidence-attachment-compiler.md`:
```bash
pytest tests/unit/test_evidence_compiler.py
pytest tests/test_catalog_fixtures.py -k "DSP016 or DSP017"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify both catalog items pass.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S08 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(evidence): implement evidence attachment size validation, magic byte mime verification, and multipart encoding (DSP016, DSP017)`

STOP CONDITIONS:
Stop immediately if magic byte detection misclassifies valid image fixtures or multipart boundaries truncate payload bytes.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S09`).
