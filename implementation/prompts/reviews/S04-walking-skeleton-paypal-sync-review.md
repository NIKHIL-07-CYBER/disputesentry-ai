ROLE: Independent auditor for stage S04 (Walking Skeleton: PayPal Client & Dispute Sync) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S04-walking-skeleton-paypal-sync.md`, `implementation/tests/S04-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S04-walking-skeleton-paypal-sync.md`.
3. Tests: confirm contract and integration tests cover all cases in `S04-tests.md`. Verify the end-to-end walking skeleton slice test exists and passes.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/contract/test_paypal_client.py tests/integration/test_dispute_sync.py
   pytest tests/test_catalog_fixtures.py -k "DSP005 or DSP010 or DSP014"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare dispute synchronization logic against `implementation/assets/flows/DISPUTE_SYNC_FLOW.md` and `implementation/assets/reference/PAYPAL_API_MATRIX.md`.
6. Quality: verify HATEOAS link check strictly enforces that `provide_evidence` link must exist before submitting evidence. Check that OAuth2 token refresh handles 401 retries cleanly.
7. Catalog items audit: re-verify `DSP005` (HATEOAS preconditions) and `DSP014` (provide-evidence dispatch) against catalog specifications and oracle expectations.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
