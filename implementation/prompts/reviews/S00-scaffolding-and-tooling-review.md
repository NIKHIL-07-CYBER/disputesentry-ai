ROLE: Independent auditor for stage S00 (Scaffolding and Tooling) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S00-scaffolding-and-tooling.md`, `implementation/tests/S00-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of the stage file (`pyproject.toml`, `requirements.txt`, `.gitignore`, `config.yaml`, `app/__init__.py`, `app/config.py`, `app/main.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/unit/test_config.py`).
3. Tests: confirm tests in `tests/unit/test_config.py` cover all cases in `implementation/tests/S00-tests.md` and were added before or with the implementation.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_config.py
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare `app/config.py` against `implementation/assets/data-models/CONFIG_SCHEMA.md` for parameter names and defaults.
6. Quality: check for unpinned dependencies, dead code, or hardcoded secrets.
7. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` (for stage-local fixes) or `utility/blocked-triage.md` (if specs need clarification).
