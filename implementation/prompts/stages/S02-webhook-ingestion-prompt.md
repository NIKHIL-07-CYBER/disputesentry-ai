ROLE: Cryptographic security engineer implementing webhook verification for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S02 (Webhook Ingestion Core) of DisputeSentry AI.
- Source of truth: `implementation/stages/S02-webhook-ingestion.md`
- Test instructions: `implementation/tests/S02-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP001`, `DSP002`, `DSP003`, `DSP004`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S02-webhook-ingestion.md`, and `implementation/tests/S02-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S01 as `review-pass`.
4. Verify catalog fixtures for `DSP001`, `DSP002`, `DSP003`, and `DSP004` exist.
5. Run baseline check (`pytest tests/test_catalog_fixtures.py`) to confirm harness is operational.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S02-webhook-ingestion.md`.
- Strictly forbidden: Never edit `catalog/` or `docs/`. Never bypass RSA-SHA256 verification in production code.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S02-webhook-ingestion.md`.
2. Write unit and integration tests first in `tests/unit/test_webhook_verifier.py` and `tests/integration/test_webhook_api.py` per `S02-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/clients/webhook_verifier.py` (domain whitelist, X.509 cert caching, RSA-SHA256 check) and `app/api/webhooks.py`.
5. Connect `DSP001`, `DSP002`, `DSP003`, `DSP004` to `tests/test_catalog_fixtures.py`.
6. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S02-webhook-ingestion.md`:
```bash
pytest tests/unit/test_webhook_verifier.py tests/integration/test_webhook_api.py
pytest tests/test_catalog_fixtures.py -k "DSP001 or DSP002 or DSP003 or DSP004"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify all four catalog items pass.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S02 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(webhooks): implement rsa-sha256 signature verification, ssrf cert whitelist, and deduplication (DSP001-DSP004)`

STOP CONDITIONS:
Stop immediately if raw byte digest verification fails due to unhandled middleware mutations or if SSRF regex requires modification.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S03`).
