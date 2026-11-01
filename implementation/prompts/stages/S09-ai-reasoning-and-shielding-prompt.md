ROLE: AI security engineer implementing structured LLM reasoning and prompt injection shields for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S09 (AI Reasoning Shielding & Prompt Injection Defense) of DisputeSentry AI.
- Source of truth: `implementation/stages/S09-ai-reasoning-and-shielding.md`
- Test instructions: `implementation/tests/S09-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP020`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S09-ai-reasoning-and-shielding.md`, and `implementation/tests/S09-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S08 as `review-pass`.
4. Verify catalog fixture for `DSP020` exists.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S09-ai-reasoning-and-shielding.md` (`app/clients/ai_client.py`, `app/domain/reasoning_shield.py`, `tests/unit/test_reasoning_shield.py`).
- Strictly forbidden: Never concatenate un-sanitized customer notes into prompts without XML tags. Never allow LLM outputs to bypass Pydantic validation.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S09-ai-reasoning-and-shielding.md`.
2. Write unit and adversarial tests first in `tests/unit/test_reasoning_shield.py` per `S09-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/domain/reasoning_shield.py`:
   - Sanitize card data with `PCISanitizer`.
   - Wrap customer notes in strict `<untrusted_customer_note>` XML tags with delimiter escaping (`DSP020`).
5. Implement `app/clients/ai_client.py`:
   - Configure Gemini Flash client with Pydantic `DisputeDecisionOutput` schema.
   - Implement deterministic heuristic fallback engine when in test environment or upon API timeout.
6. Connect `DSP020` to `tests/test_catalog_fixtures.py`.
7. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S09-ai-reasoning-and-shielding.md`:
```bash
pytest tests/unit/test_reasoning_shield.py
pytest tests/test_catalog_fixtures.py -k "DSP020"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify 0% adversarial override compromise rate.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S09 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(ai): implement gemini structured reasoning client, xml boundary isolation, and prompt injection shield (DSP020)`

STOP CONDITIONS:
Stop immediately if an adversarial prompt injection payload causes the model to recommend concession contrary to verified tracking records.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S10`).
