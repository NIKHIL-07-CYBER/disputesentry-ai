ROLE: Expert Python systems engineer initializing workspace scaffolding for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S00 (Scaffolding and Tooling) of DisputeSentry AI.
- Source of truth: `implementation/stages/S00-scaffolding-and-tooling.md`
- Test instructions: `implementation/tests/S00-tests.md`
- Router: `implementation/MASTER.md`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S00-scaffolding-and-tooling.md`, and `implementation/tests/S00-tests.md`.
2. Read Section 3 ("Read first") of `implementation/stages/S00-scaffolding-and-tooling.md` in order.
3. Verify Python 3.11+ is installed (`python --version`).
4. S00 has no predecessor stages; confirm `implementation/PROGRESS.md` shows all stages as `not-started`.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S00-scaffolding-and-tooling.md` (`pyproject.toml`, `requirements.txt`, `.gitignore`, `config.yaml`, `app/__init__.py`, `app/config.py`, `app/main.py`, `tests/__init__.py`, `tests/conftest.py`, `tests/unit/test_config.py`).
- Strictly forbidden: Never touch `catalog/` or `docs/`. Never add unpinned dependencies.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S00-scaffolding-and-tooling.md`.
2. Initialise project workspace exactly as Section 7 specifies.
3. Write `tests/unit/test_config.py` first per `implementation/tests/S00-tests.md`. Verify it fails.
4. Implement `requirements.txt`, `pyproject.toml`, `app/config.py`, and `app/main.py` (`GET /health`).
5. Run tests, linter (`ruff`), and type checker (`mypy`) until 100% green.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S00-scaffolding-and-tooling.md`:
```bash
pytest tests/unit/test_config.py
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify every criterion explicitly.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S00 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`chore(scaffold): initialize python 3.11 workspace, dependencies, config and health check`

STOP CONDITIONS:
Stop immediately if a required dependency is missing from `DEPENDENCIES.md` or a file outside the allowlist must be touched. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S01`).
