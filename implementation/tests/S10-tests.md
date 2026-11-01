# S10 tests: Web API & Merchant Operator Dashboard

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T10-01` | Dashboard HTML page load | `GET /dashboard` | HTTP 200 OK, `text/html`, contains `DisputeSentry AI` and table header |
| `T10-02` | Queue sorting by urgency and amount | Multiple disputes with varied due dates and amounts | Disputes rendered sorted by `hours_until_due ASC` and `dispute_amount DESC` |
| `T10-03` | Dispute detail modal inspection | `GET /api/disputes/{id}` | Returns complete JSON including audit trail and evidence package |
| `T10-04` | Metrics summary endpoint | `GET /api/metrics` | Returns HTTP 200 `{"win_rate": float, "net_recovery_rate": float, "total_saved_usd": float}` |

## Positive cases
- Operator dashboard renders cleanly in desktop viewport without missing templates.
- Approving a dispute via UI triggers POST `/api/disputes/{id}/approve` and updates status badge.

## Negative cases
- Accessing non-existent dispute ID returns 404 with error message in modal.

## Boundary cases
- Empty dispute queue renders empty-state banner ("No active disputes pending").

## Fixtures and golden files used
- `app/templates/dashboard.html`
- `tests/conftest.py`

## Commands to run (exact)
```bash
pytest tests/integration/test_dashboard_api.py -v
```

## Coverage target
- 90%+ coverage across `app/api/dashboard.py` and `app/api/disputes.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Injecting un-escaped customer strings into Jinja2 templates without auto-escaping (XSS risk).
- Missing static asset routing for CSS/JS files.
