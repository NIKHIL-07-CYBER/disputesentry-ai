ROLE: Full-stack integration engineer implementing the walking skeleton slice for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S04 (Walking Skeleton: PayPal Client & Dispute Sync) of DisputeSentry AI.
- Source of truth: `implementation/stages/S04-walking-skeleton-paypal-sync.md`
- Test instructions: `implementation/tests/S04-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP005`, `DSP010`, `DSP014`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S04-walking-skeleton-paypal-sync.md`, and `implementation/tests/S04-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S03 as `review-pass`.
4. Verify catalog fixtures for `DSP005`, `DSP010`, and `DSP014` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S04-walking-skeleton-paypal-sync.md` (`app/clients/paypal_client.py`, `app/services/dispute_sync.py`, `tests/contract/test_paypal_client.py`, `tests/integration/test_dispute_sync.py`).
- Strictly forbidden: Never bypass HATEOAS link checks. Never hardcode live API credentials.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S04-walking-skeleton-paypal-sync.md`.
2. Write tests first in `tests/contract/test_paypal_client.py` and `tests/integration/test_dispute_sync.py` per `S04-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/clients/paypal_client.py` (OAuth2 token cache, dispute retrieval, evidence submission).
5. Implement `app/services/dispute_sync.py` (HATEOAS validation, deadline calculation, end-to-end sync).
6. Connect `DSP005`, `DSP010`, `DSP014` to `tests/test_catalog_fixtures.py`.
7. Execute and record the end-to-end demo command connecting webhook ingestion to PayPal client dispatch.
8. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S04-walking-skeleton-paypal-sync.md`:
```bash
pytest tests/contract/test_paypal_client.py tests/integration/test_dispute_sync.py
pytest tests/test_catalog_fixtures.py -k "DSP005 or DSP010 or DSP014"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify the recorded end-to-end walking skeleton slice succeeds.

RECORDED DEMO COMMAND (Walking Skeleton Milestone):
Run: `pytest tests/integration/test_dispute_sync.py -k "test_walking_skeleton_end_to_end" -v -s`
Expected Output:
```
PASSED tests/integration/test_dispute_sync.py::test_walking_skeleton_end_to_end
End-to-end slice verified: Webhook -> Order Lookup -> HATEOAS Link Checked -> Evidence Dispatched (200 OK)
```

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S04 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(sync): implement paypal client, hateoas link check, deadline urgency, and walking skeleton (DSP005, DSP010, DSP014)`

STOP CONDITIONS:
Stop immediately if HATEOAS link validation or OAuth2 token refresh fails. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, demo command output, deviations (none), and next stage ID (`S05`).
