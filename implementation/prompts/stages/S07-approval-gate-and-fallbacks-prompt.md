ROLE: High-reliability systems engineer implementing approval gates and fail-safe daemons for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S07 (Human-in-the-Loop Approval Gate & Safe Fallbacks) of DisputeSentry AI.
- Source of truth: `implementation/stages/S07-approval-gate-and-fallbacks.md`
- Test instructions: `implementation/tests/S07-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP013`, `DSP015`, `DSP018`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S07-approval-gate-and-fallbacks.md`, and `implementation/tests/S07-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S06 as `review-pass`.
4. Verify catalog fixtures for `DSP013`, `DSP015`, and `DSP018` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S07-approval-gate-and-fallbacks.md` (`app/services/approval_gate.py`, `app/services/deadline_monitor.py`, `app/api/approvals.py`, test files).
- Strictly forbidden: Never allow automatic dispatch of disputes >= $100 or concessions without operator approval (unless deadline fallback triggers). Never touch `catalog/` or `docs/`.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S07-approval-gate-and-fallbacks.md`.
2. Write integration and unit tests first per `S07-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/services/approval_gate.py` (financial gate locks, state transitions).
5. Implement `app/api/approvals.py` (`POST /api/disputes/{id}/approve` and `/reject`).
6. Implement `app/services/deadline_monitor.py` (2-hour fail-safe automatic evidence dispatch).
7. Connect `DSP013`, `DSP015`, `DSP018` to `tests/test_catalog_fixtures.py`.
8. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S07-approval-gate-and-fallbacks.md`:
```bash
pytest tests/integration/test_approval_gate.py tests/unit/test_deadline_monitor.py
pytest tests/test_catalog_fixtures.py -k "DSP013 or DSP015 or DSP018"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify all three catalog items pass.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S07 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(oversight): implement human approval gate, concession executor, and 2-hour deadline fail-safe (DSP013, DSP015, DSP018)`

STOP CONDITIONS:
Stop immediately if state machine permits unlawful state transitions or fail-safe daemon encounters race condition locks.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S08`).
