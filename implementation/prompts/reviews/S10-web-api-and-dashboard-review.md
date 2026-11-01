ROLE: Independent auditor for stage S10 (Web API & Merchant Operator Dashboard) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S10-web-api-and-dashboard.md`, `implementation/tests/S10-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S10-web-api-and-dashboard.md` (`app/api/dashboard.py`, `app/api/disputes.py`, `app/api/metrics.py`, `app/templates/`, `app/static/`, `app/main.py`, `tests/integration/test_dashboard_api.py`).
3. Tests: confirm integration tests in `tests/integration/test_dashboard_api.py` cover all cases in `S10-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/integration/test_dashboard_api.py
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare UI templates against `docs/SPEC.md` §4.2.4 requirements (urgency-sorted table, Approve/Reject controls, modal inspection).
6. Quality: confirm Jinja2 auto-escaping is active to prevent XSS. Verify no sensitive PAN or CVV is rendered. Check responsive viewport behavior.
7. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
