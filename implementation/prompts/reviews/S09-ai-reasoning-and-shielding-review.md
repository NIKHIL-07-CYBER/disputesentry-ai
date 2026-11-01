ROLE: Independent auditor for stage S09 (AI Reasoning Shielding & Prompt Injection Defense) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S09-ai-reasoning-and-shielding.md`, `implementation/tests/S09-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S09-ai-reasoning-and-shielding.md` (`app/clients/ai_client.py`, `app/domain/reasoning_shield.py`, `tests/unit/test_reasoning_shield.py`).
3. Tests: confirm tests in `tests/unit/test_reasoning_shield.py` cover all cases in `S09-tests.md`, specifically prompt injection and XML boundary escaping.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_reasoning_shield.py
   pytest tests/test_catalog_fixtures.py -k "DSP020"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare LLM shielding against `implementation/assets/flows/AI_REASONING_FLOW.md` and `docs/SECURITY.md` §1.
6. Quality: confirm customer text is wrapped inside `<untrusted_customer_note>` tags and stripped of cardholder data before prompt assembly. Confirm LLM outputs parse strictly into Pydantic `DisputeDecisionOutput` with deterministic fallback.
7. Catalog items audit: re-verify `DSP020` (prompt injection defense) against catalog specifications and oracle expectations; ensure adversarial notes cannot force concession when tracking shows delivery.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
