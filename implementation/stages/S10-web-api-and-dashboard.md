# S10 Web API & Merchant Operator Dashboard

## 1 Goal and outcome
Implement the merchant operator web dashboard (`app/api/dashboard.py`, Jinja2 templates, static assets) providing a real-time priority queue sorted by deadline urgency, one-click Approve/Reject buttons, evidence inspection modal, and historical metrics summary.

## 2 Entry conditions
- Stage S09 complete (`DSP020` passing).
- Jinja2 installed and importable.

## 3 Read first
1. `docs/SPEC.md` §4.2.4
2. `implementation/assets/architecture/REPO_LAYOUT.md`
3. `implementation/assets/flows/APPROVAL_GATE_FLOW.md`
4. `implementation/tests/S10-tests.md`

## 4 Files to create or modify
- `app/api/dashboard.py`
- `app/api/disputes.py`
- `app/api/metrics.py`
- `app/templates/base.html`
- `app/templates/dashboard.html`
- `app/templates/dispute_detail.html`
- `app/static/css/style.css`
- `app/static/js/app.js`
- `app/main.py` (mount static and template routes)
- `tests/integration/test_dashboard_api.py`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- Never disable auto-escaping in Jinja2 templates.
- Never render raw PAN/CVV in HTML templates.

## 6 Interfaces and signatures
```python
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

router = APIRouter()

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request) -> HTMLResponse: ...

@router.get("/api/disputes/{dispute_id}")
async def get_dispute_detail(dispute_id: str) -> dict: ...

@router.get("/api/metrics")
async def get_metrics_summary() -> dict: ...
```

## 7 Step-by-step instructions
1. Write tests in `tests/integration/test_dashboard_api.py` per `S10-tests.md`. Verify they fail.
2. Create `app/templates/base.html` with Tailwind CSS CDN, header bar, and layout container.
3. Create `app/templates/dashboard.html` rendering:
   - Summary metric cards (Total At Risk, Pending Approvals, Win Rate %, Net Recovery %).
   - Dispute priority table sorted by `hours_until_due ASC` and `amount DESC`.
   - Action buttons (Approve / Reject) triggering AJAX API calls.
4. Create `app/templates/dispute_detail.html` rendering modal with tracking evidence, AI reasoning justification, and audit history.
5. Create `app/static/js/app.js` with polling refresh (every 10s) and modal toggle logic.
6. Implement `app/api/dashboard.py`, `app/api/disputes.py`, and `app/api/metrics.py`.
7. Wire routers and static file mounts in `app/main.py`.
8. Run tests until 100% green.

## 8 Edge cases
- Dispute with 0 active items renders clean empty state.
- Special characters in customer notes properly escaped against XSS attacks.

## 9 Out of scope
- Docker packaging and release verification (handled in S11).

## 10 Tests
Follow instructions in `implementation/tests/S10-tests.md`.

## 11 Exit criteria
- Dashboard renders HTTP 200 with all template components.
- API endpoints `/api/disputes/{id}` and `/api/metrics` return valid JSON.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 12 Commit message
`feat(ui): implement jinja2 merchant operator dashboard, dispute detail modal, and metrics api`

## 13 Failure and rollback handling
If template loading fails, verify `Jinja2Templates(directory="app/templates")` path resolution across operating systems.

## 14 Common AI-agent pitfalls for this stage
- Forgetting to mount `StaticFiles(directory="app/static")` in `app/main.py`.
- Using raw string formatting instead of Jinja2 template rendering.

## 15 Handoff notes for the next stage
Provides complete web user interface for S11 (Hardening and Release).
