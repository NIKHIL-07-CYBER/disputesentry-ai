# Architectural Decision Records (ADR) Index

| ADR ID | Title | Status | Date | Summary |
|---|---|---|---|---|
| [ADR-001](file:///D:/fix/challenges/paypal/docs/adr/ADR-001-language-and-stack.md) | Language and Stack Selection | Accepted | 2026-11-01 | Python 3.11+, FastAPI, Pydantic v2, SQLite 3 (WAL mode), httpx, cryptography, and Jinja2 for zero-ops local run and typed validation. |
| [ADR-002](file:///D:/fix/challenges/paypal/docs/adr/ADR-002-integration-strategy.md) | Integration Strategy | Accepted | 2026-11-01 | Direct async REST client (`httpx`) for PayPal Disputes API v1 and webhook verification; MCP tool adapter layer for external agent interactions. |
| [ADR-003](file:///D:/fix/challenges/paypal/docs/adr/ADR-003-scope-and-versions.md) | Scope and Version Policy | Accepted | 2026-11-01 | Pinned to PayPal Disputes API v1; focus on physical goods disputes (INR, SNAD, Unauthorised); seeded relational SQLite records for hackathon demo. |
| [ADR-004](file:///D:/fix/challenges/paypal/docs/adr/ADR-004-verification-strategy.md) | Verification Strategy | Accepted | 2026-11-01 | Automated 4-tier testing hierarchy with offline deterministic golden fixture runner (< 3s runtime) and zero-network CI test execution. |
