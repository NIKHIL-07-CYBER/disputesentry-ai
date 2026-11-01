ROLE: Independent auditor for stage S11 (System Hardening, Sandbox Validation & Release) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S11-hardening-and-release.md`, `implementation/tests/S11-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S11-hardening-and-release.md` (`Dockerfile`, `docker-compose.yaml`, `README.md`, `run_sandbox_eval.py`, `tests/integration/test_release_smoke.py`).
3. Tests: confirm complete test runner (`pytest tests/test_catalog_fixtures.py`) passes 22 of 22 items and coverage is $\ge 90\%$.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest --cov=app --cov-report=term-missing tests/
   pytest tests/test_catalog_fixtures.py
   ruff check .
   mypy --strict app/
   docker build -t disputesentry-ai .
   ```
5. Drift: compare documentation against `README.md` and `docs/CI_RELEASE.md`. Confirm run instructions work from a clean clone.
6. Quality: verify zero unmasked card numbers exist across the database and test logs. Confirm Docker container boots and responds to `/health`.
7. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If PASS, state that the project is ready for final acceptance audit (`utility/final-acceptance.md`).
