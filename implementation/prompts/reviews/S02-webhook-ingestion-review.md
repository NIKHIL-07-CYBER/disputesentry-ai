ROLE: Independent auditor for stage S02 (Webhook Ingestion Core) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S02-webhook-ingestion.md`, `implementation/tests/S02-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S02-webhook-ingestion.md`.
3. Tests: confirm tests in `tests/unit/test_webhook_verifier.py` and `tests/integration/test_webhook_api.py` cover all cases in `S02-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_webhook_verifier.py tests/integration/test_webhook_api.py
   pytest tests/test_catalog_fixtures.py -k "DSP001 or DSP002 or DSP003 or DSP004"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare verifier logic against `implementation/assets/flows/WEBHOOK_INGESTION_FLOW.md`. Verify raw request bytes are preserved before digest hashing.
6. Quality: verify cert URL whitelist strictly checks `^https://api(\.sandbox)?\.paypal\.com/` to prevent SSRF. Confirm zero unmasked PAN/CVV logging.
7. Catalog items audit: re-verify `DSP001` (valid signature verification) and `DSP004` (cert domain whitelist) against their catalog specifications and oracle expectations; confirm code matches the catalog intent, not just mock shortcuts.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
