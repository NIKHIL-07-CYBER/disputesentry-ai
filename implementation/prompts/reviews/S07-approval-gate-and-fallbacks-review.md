ROLE: Independent auditor for stage S07 (Human-in-the-Loop Approval Gate & Safe Fallbacks) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S07-approval-gate-and-fallbacks.md`, `implementation/tests/S07-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S07-approval-gate-and-fallbacks.md`.
3. Tests: confirm tests in `tests/integration/test_approval_gate.py` and `tests/unit/test_deadline_monitor.py` cover all cases in `S07-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/integration/test_approval_gate.py tests/unit/test_deadline_monitor.py
   pytest tests/test_catalog_fixtures.py -k "DSP013 or DSP015 or DSP018"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare state machine transitions against `implementation/assets/flows/APPROVAL_GATE_FLOW.md`.
6. Quality: verify that disputes with amount $\ge \$100.00$ or action `CONCEDE` CANNOT transition to `DISPATCHED` autonomously without operator sign-off (unless 2-hour fail-safe triggers). Check that deadline daemon activates when `hours_until_due <= 2.0`.
7. Catalog items audit: re-verify `DSP013` ($100 gate) and `DSP018` (fail-safe emergency fallback) against catalog specifications and oracle expectations.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
