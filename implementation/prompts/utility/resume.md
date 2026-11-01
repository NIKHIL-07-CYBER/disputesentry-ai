ROLE: You continue an interrupted implementation stage of DisputeSentry AI. You have no memory of the earlier session.

1. Read `implementation/MASTER.md`, `AGENTS.md`, and `implementation/PROGRESS.md`. Identify the stage marked `in-progress` (or the one the user names).
2. Read that stage's file in `implementation/stages/` and tests file in `implementation/tests/`.
3. Run `git status` and `git log -10`. Diff the working tree against the stage's allowlist in Section 4 of its stage file; list any file touched outside it.
4. Find the last green step: run the build, lint, and the stage's tests; walk the stage's numbered steps in Section 7 and mark each as done, partial, or not started, based on concrete evidence in the tree, not on assumptions.
5. Continue from the first incomplete step. Do not redo finished steps. Do not rewrite files that already satisfy their step.
6. Finish with the stage's exit criteria and close-out (updating `implementation/PROGRESS.md` and using the exact commit message from Section 12).
7. If a file outside the allowlist was touched or the tree is in a state you cannot explain, STOP and report using the blocked protocol; do not guess.

Final report:
- Steps found done
- Steps completed now
- Exit-command output
- Deviations
