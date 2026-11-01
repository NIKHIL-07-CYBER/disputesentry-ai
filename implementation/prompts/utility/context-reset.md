ROLE: You close out a long or confused session of DisputeSentry AI so a fresh session can take over cleanly.

1. Read `implementation/PROGRESS.md` and run `git status` and `git log -10`.
2. Do not start any new work. If a stage is mid-flight, do not attempt to finish it.
3. Append to the stage's row in `implementation/PROGRESS.md` Notes column: what is done, what is half-done (with file paths), the exact next step, and any regression traps discovered.
4. If the working tree has uncommitted changes that pass the build, lint, and tests, do not commit them; list them in your report. If the build or tests are red, state the failing test explicitly.
5. Print:
   a) The exact files the next session must read, in order.
   b) The exact prompt to paste next (usually `implementation/prompts/utility/resume.md`).
   c) Any decision requiring operator clarification.
Then stop.
