# ADR-001: Language and Stack Selection
Status: accepted
Date: 2026-11-01

## Context
DisputeSentry AI requires an application stack capable of:
1. Ingesting and cryptographically verifying high-throughput, latency-sensitive PayPal Webhooks (`POST /webhooks/paypal`).
2. Orchestrating REST API interactions with the PayPal Disputes API v1 (OAuth2 client credentials token lifecycle, GET disputes, multipart POST evidence, accept claim).
3. Querying local relational merchant records (orders, tracking, delivery status, customer conversations).
4. Executing an AI reasoning engine that takes untrusted customer dispute text and merchant evidence, parses it against Seller Protection rules, and returns strictly typed structured JSON recommendations.
5. Providing a clean, real-time web dashboard for merchant operators to monitor response deadlines (`seller_response_due_date`), review pending approvals, and inspect immutable audit trails.
6. Ensuring maximum verifiability for AI-generated code through rigorous type safety, zero-dependency local test harnesses, and deterministic contract testing within the 11-day hackathon window [17][18].

Sources:
- Python 3.11+ Documentation: https://docs.python.org/3.11/
- FastAPI Framework: https://fastapi.tiangolo.com/
- Pydantic v2 Architecture: https://docs.pydantic.dev/latest/
- PayPal Agent Toolkit: https://developer.paypal.com/tools/agent-toolkit

## Decision
We select **Python 3.11+** with **FastAPI**, **Pydantic v2**, **aiosqlite / SQLite 3**, **httpx**, **cryptography**, and **Jinja2 / modern responsive CSS (HTML/Tailwind via CDN)** as the core technology stack.

Key libraries and pinned ecosystem components:
- Web framework: `fastapi >= 0.115.0`, `uvicorn >= 0.32.0`
- Data validation and JSON schemas: `pydantic >= 2.9.0`, `pydantic-settings >= 2.5.0`
- HTTP client & PayPal API connector: `httpx >= 0.27.0` (async connection pooling, multipart support)
- Cryptographic verification: `cryptography >= 43.0.0` (PayPal X.509 cert validation, RSA-SHA256 signature verification)
- Local datastore & audit logging: `aiosqlite >= 0.20.0` with SQLite 3 (WAL mode enabled, zero-ops local reproducibility)
- Templating & Merchant UI: `jinja2 >= 3.1.4` (server-rendered responsive dashboard with auto-refreshing polling/SSE)
- AI Reasoning Provider: `google-genai >= 0.1.1` (Gemini 2.5/1.5 Flash structured output mode) with a deterministic heuristic fallback engine.
- Test and verification harness: `pytest >= 8.3.0`, `pytest-asyncio >= 0.24.0`, `pytest-mock >= 3.14.0`

## Alternatives considered
1. **TypeScript / Node.js (Express or Fastify + React)**
   - *Why it lost:* React adds frontend build toolchains (Vite/Node/npm bundling) that introduce setup friction for hackathon judges running the application locally. Python provides a unified single-runtime deployment (server, AI pipeline, database, UI) and has first-class native cryptographic support for X.509 cert verification.
2. **Go (Gin / Chi + SQLite)**
   - *Why it lost:* While Go produces excellent single binaries, Python's dynamic fixture handling, rich ecosystem for structured LLM parsing (Pydantic v2 instructor/genai bindings), and concise test idioms provide substantially higher velocity and verification safety during rapid iteration.
3. **External Relational Database (PostgreSQL / MySQL)**
   - *Why it lost:* Requires external Docker containers or cloud connection strings, violating the requirement for instant, zero-friction local execution for hackathon judges and deterministic automated fixture testing. SQLite in WAL mode satisfies all local data isolation and concurrency needs.

## Consequences
- **Positive:**
  - Zero-friction developer setup: running `python -m uvicorn app.main:app` or a single container immediately spins up the web server, seeded SQLite database, webhook receiver, and web dashboard.
  - Strict type checking and JSON schema generation through Pydantic v2 ensures that every API request, internal domain model, and LLM output is mechanically validated at runtime.
  - Test suites run in milliseconds using in-memory or temporary SQLite databases without external network dependencies.
- **Negative / Constraints to Watch:**
  - Python runtime environment requires careful virtualenv / dependency management (must pin versions strictly in `requirements.txt`).
  - SQLite concurrent write throughput is limited compared to Postgres; sufficient for SMB merchant dispute volumes (hundreds of disputes/day) but requires connection serialize gates in write-heavy workloads.
