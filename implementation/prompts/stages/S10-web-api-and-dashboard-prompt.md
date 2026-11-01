ROLE: Full-stack web engineer implementing the merchant operator dashboard for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S10 (Web API & Merchant Operator Dashboard) of DisputeSentry AI.
- Source of truth: `implementation/stages/S10-web-api-and-dashboard.md`
- Test instructions: `implementation/tests/S10-tests.md`
- Router: `implementation/MASTER.md`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S10-web-api-and-dashboard.md`, and `implementation/tests/S10-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S09 as `review-pass`.
4. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S10-web-api-and-dashboard.md` (`app/api/dashboard.py`, `app/api/disputes.py`, `app/api/metrics.py`, `app/templates/`, `app/static/`, `app/main.py`, `tests/integration/test_dashboard_api.py`).
- Strictly forbidden: Never disable Jinja2 auto-escaping. Never render raw card numbers or CVVs in HTML. Never touch `catalog/` or `docs/`.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S10-web-api-and-dashboard.md`.
2. Write integration tests first in `tests/integration/test_dashboard_api.py` per `S10-tests.md`. Verify they fail.
3. Create Jinja2 templates (`base.html`, `dashboard.html`, `dispute_detail.html`) with responsive Tailwind layout.
4. Implement static assets (`app/static/css/style.css`, `app/static/js/app.js`).
5. Implement endpoints:
   - `GET /dashboard` (urgency-sorted priority dispute queue).
   - `GET /api/disputes/{id}` (evidence modal data).
   - `GET /api/metrics` (win rate and net recovery metrics).
6. Mount routes and static directories in `app/main.py`.
7. Run tests until 100% green.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S10-web-api-and-dashboard.md`:
```bash
pytest tests/integration/test_dashboard_api.py
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify dashboard renders cleanly and returns HTTP 200.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S10 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(ui): implement jinja2 merchant operator dashboard, dispute detail modal, and metrics api`

STOP CONDITIONS:
Stop immediately if template resolution fails or static files cannot be served. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S11`).
