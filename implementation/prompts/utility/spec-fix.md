ROLE: You apply one confirmed spec correction to DisputeSentry AI.

Precondition: The user has confirmed the fix (the triage report or user message names the approved change). If not, STOP and ask for confirmation.

1. Edit the highest-precedence wrong file (`catalog/*.yaml` > `docs/SPEC.md` > `docs/ARCHITECTURE.md` > ADRs). For catalog changes, cite the official PayPal source and set `verification_status` accurately; update the item's fixtures in `catalog/fixtures/` and `expected.yaml` if the expected outcome changed.
2. Update every dependent lower-precedence file: `implementation/stages/`, `implementation/tests/`, `implementation/assets/`, and prompts that quote it. Search for the old value across the repository; no stale references may remain.
3. Re-run affected audits:
   - Path audit: all referenced paths exist.
   - Terminology audit: names, IDs, flags identical.
   - Coverage audit: every catalog ID is still owned by exactly one stage and tested.
4. Log the change in `docs/OPEN_QUESTIONS.md` (resolve an existing entry or add a new one) explaining what changed, why, and what was affected.
5. Make exactly one git commit with message: `spec-fix: <what changed>`. Touch no application source code.
6. Update `implementation/PROGRESS.md`: if a stage was blocked by this, set its status back to `not-started` (or `in-progress` if it has partial work) and append an entry in the Log section.

Output format:
- Files changed
- Audits run with results
- Commit hash
- Which stage can resume
