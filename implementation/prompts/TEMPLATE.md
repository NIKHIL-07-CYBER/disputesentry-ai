# Stage Prompt Template

Every stage execution prompt in `implementation/prompts/stages/` must follow this nine-section structure and remain under 120 lines.

---

ROLE: Expert Python implementation engineer for stage S## (<name>) of DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S## (<name>) of DisputeSentry AI.
- Source of truth: `implementation/stages/S##-<slug>.md`
- Test instructions: `implementation/tests/S##-tests.md`
- Router: `implementation/MASTER.md`

PRE-FLIGHT: Do these steps before writing any code and print the results:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S##-<slug>.md`, and `implementation/tests/S##-tests.md`.
2. Read all files listed in Section 3 ("Read first") of the stage file in exact order.
3. Verify the stage entry conditions with the specified check commands.
4. Confirm `implementation/PROGRESS.md` shows every dependency of this stage as `review-pass`.
5. Run the baseline test and lint commands to confirm the workspace is green.
If any pre-flight check fails, STOP immediately and report using the blocked protocol in `implementation/MASTER.md`.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 ("Files to create or modify") of `implementation/stages/S##-<slug>.md`.
- Strictly forbidden: Never edit `catalog/`, `docs/`, or files owned by other stages. Never add new dependencies beyond `implementation/assets/architecture/DEPENDENCIES.md`. Avoid scope creep.

METHOD:
1. Review the regression traps in Section 14 of the stage file and `implementation/tests/S##-tests.md`.
2. Write test cases first in the tests directory specified in `implementation/tests/S##-tests.md`. Run pytest to confirm tests fail (Red phase).
3. Implement minimal production code following the step-by-step instructions in Section 7 of the stage file.
4. Run tests after each step to verify progression (Green phase). Keep diffs small.

EXIT CRITERIA:
Execute all exit-criteria commands listed in Section 11 of `implementation/stages/S##-<slug>.md`.
Paste real terminal output. Verify every criterion explicitly. Never claim success without pasted output.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set status to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12 of `implementation/stages/S##-<slug>.md`.
3. Update handoff notes in Section 15 of the stage file if any implementation details deviate or need clarification.

STOP CONDITIONS:
Stop immediately without improvising if:
- A spec or requirement appears ambiguous or contradictory.
- An oracle test fails and suggests a discrepancy in a catalog item.
- A required change falls outside the allowlist.
- An unlisted dependency is required.
Follow the Spec Change or Blocked Protocol in `implementation/MASTER.md`.

FINAL REPORT:
Print a structured report containing:
1. Files created or modified.
2. Tests added (with Test IDs).
3. Exit-command outputs.
4. Deviations (should be none).
5. Open questions or blockers (if any).
6. Next stage ID.
