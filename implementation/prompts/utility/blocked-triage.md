ROLE: You diagnose a stopped or failed stage of DisputeSentry AI. You do not fix anything yet.

1. Read `implementation/MASTER.md` and the failing stage's file in `implementation/stages/` and tests file in `implementation/tests/`. Read the failure report the user pasted (or the last entry for that stage in `implementation/ORCHESTRATION_LOG.md` and `implementation/PROGRESS.md`).
2. Reproduce the failure with the exact failing command. Capture the terminal output.
3. Classify the blocker as exactly one of:
   a) stage-local bug (the code is wrong, the spec is right);
   b) wrong or ambiguous spec (`docs/SPEC.md`, an ADR, or the stage file is wrong or silent);
   c) wrong catalog entry (the oracle disagrees with a catalog item; check the item's cited source and the oracle result before concluding);
   d) environment (tooling, container, network, version);
   e) missing dependency not in the plan.
4. Gather evidence for the classification: command output, the relevant spec lines, and the cited documentation source.
5. Propose the minimal fix: the exact file to change and the exact change. For (b) and (c) name the highest-precedence file that must change (`catalog/*.yaml` > `docs/SPEC.md` > `docs/ARCHITECTURE.md` > ADRs > `implementation/*`).
6. DO NOT apply the fix. For (a) and (d) recommend `implementation/prompts/utility/resume.md`. For (b), (c), and (e) recommend `implementation/prompts/utility/spec-fix.md` after the user confirms.

Output format:
- Classification
- Evidence
- Proposed change
- Recommended next prompt
