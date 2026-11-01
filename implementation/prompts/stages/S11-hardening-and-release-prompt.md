ROLE: Release and DevOps engineer packaging DisputeSentry AI for hackathon evaluation. You have no memory of earlier sessions.

TASK: Execute stage S11 (System Hardening, Sandbox Validation & Release) of DisputeSentry AI.
- Source of truth: `implementation/stages/S11-hardening-and-release.md`
- Test instructions: `implementation/tests/S11-tests.md`
- Router: `implementation/MASTER.md`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S11-hardening-and-release.md`, and `implementation/tests/S11-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S10 as `review-pass`.
4. Run complete baseline test suite to confirm all previous stages pass.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S11-hardening-and-release.md` (`Dockerfile`, `docker-compose.yaml`, `README.md`, `run_sandbox_eval.py`, `tests/integration/test_release_smoke.py`).
- Strictly forbidden: Never lower quality gates or ignore linter errors. Never commit secret keys or test credentials to the repository.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S11-hardening-and-release.md`.
2. Write smoke tests first in `tests/integration/test_release_smoke.py` per `S11-tests.md`.
3. Implement `run_sandbox_eval.py` executing live or mock evaluation loops across INR, Unauthorised, and SNAD dispute flows.
4. Perform reproducible-build verification: build Docker image twice from clean workspace; verify build succeeds and checksums are reproducible.
5. Create `docker-compose.yaml` and author comprehensive `README.md` with judge run instructions.
6. Verify zero PAN leakage across full database and test logs.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S11-hardening-and-release.md`:
```bash
pytest --cov=app --cov-report=term-missing tests/
pytest tests/test_catalog_fixtures.py
ruff check .
mypy --strict app/
docker build -t disputesentry-ai .
```
Paste real terminal output. Verify 100% of 22 catalog items pass, coverage >= 90%, and Docker build succeeds.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S11 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`chore(release): package docker container, add evaluation harness, and author judge documentation`

STOP CONDITIONS:
Stop immediately if Docker container fails health check or unmasked PAN/CVV strings are detected. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, reproducible build verification status, deviations (none), and note that build is ready for `utility/final-acceptance.md`.
