# Repository Layout: DisputeSentry AI

This document defines the final file and directory structure of the repository once all implementation stages are completed.

```
disputesentry-ai/
├── .gitignore                      # Git ignore patterns for Python, SQLite, environment files
├── pyproject.toml                  # Tool configurations (ruff, mypy, pytest)
├── requirements.txt                # Pinned production and test dependencies
├── config.yaml                     # Application settings and environment defaults
├── Dockerfile                      # Standalone container specification
├── docker-compose.yaml             # Multi-service local test runner
├── README.md                       # Installation, run instructions, and hackathon judge guide
│
├── app/                            # Core application package
│   ├── __init__.py                 # Package root and version metadata
│   ├── main.py                     # FastAPI application entrypoint and middleware
│   ├── config.py                   # Pydantic BaseSettings configuration loader
│   │
│   ├── api/                        # HTTP API endpoints and routes
│   │   ├── __init__.py
│   │   ├── webhooks.py             # POST /webhooks/paypal endpoint
│   │   ├── disputes.py             # GET /api/disputes and detail routes
│   │   ├── approvals.py            # POST /api/disputes/{id}/approve & /reject
│   │   ├── metrics.py              # GET /api/metrics endpoint
│   │   └── dashboard.py            # Jinja2 HTML route for merchant UI
│   │
│   ├── clients/                    # External HTTP clients and cryptographic tools
│   │   ├── __init__.py
│   │   ├── paypal_client.py        # Async PayPal Disputes API v1 client
│   │   ├── webhook_verifier.py     # PayPal X.509 RSA-SHA256 signature verifier
│   │   └── ai_client.py            # Gemini client with structured Pydantic output
│   │
│   ├── domain/                     # Pure business logic and rule engines
│   │   ├── __init__.py
│   │   ├── models.py               # Core Pydantic domain models
│   │   ├── seller_protection.py    # PayPal Seller Protection deterministic rules
│   │   ├── economics.py            # Net Expected Recovery ROI calculation engine
│   │   └── reasoning_shield.py     # Prompt injection isolation and customer text sanitizer
│   │
│   ├── services/                   # Application orchestration and persistence workflows
│   │   ├── __init__.py
│   │   ├── dispute_sync.py         # Webhook to dispute ingestion coordinator
│   │   ├── approval_gate.py        # High-value human-in-the-loop state machine
│   │   ├── deadline_monitor.py     # 2-hour urgency fail-safe background task
│   │   ├── evidence_compiler.py    # Multipart file and JSON attachment compiler
│   │   ├── sanitizer.py            # PCI DSS Luhn cardholder and CVV regex scrubber
│   │   ├── audit_service.py        # Append-only SHA-256 chained audit logger
│   │   └── metrics_service.py      # Win-rate and recovery computation
│   │
│   ├── storage/                    # Database models and data access layer
│   │   ├── __init__.py
│   │   ├── database.py             # SQLite WAL connection manager and migrations
│   │   ├── repository.py           # Relational queries for disputes, orders, audits
│   │   └── seed_data.py            # Seeded merchant orders, tracking, and logs
│   │
│   ├── templates/                  # Jinja2 HTML templates for operator UI
│   │   ├── base.html               # Main layout and navigation header
│   │   ├── dashboard.html          # Priority-ranked dispute table and metrics cards
│   │   └── dispute_detail.html     # Evidence package inspection and approval modal
│   │
│   └── static/                     # Static CSS, JS, and vendor assets
│       ├── css/
│       │   └── style.css           # Custom styles complementing Tailwind CDN
│       └── js/
│           └── app.js              # Polling refresh and approval action handlers
│
├── catalog/                        # Behavior catalog specification
│   ├── _schema.json                # JSON schema for catalog items
│   ├── DSP001.yaml - DSP022.yaml   # 22 individual behavior specifications
│   └── fixtures/                   # Golden input/output fixtures
│       └── DSP001/ - DSP022/       # good.json, bad.json, expected.yaml
│
├── docs/                           # Preflight foundation documents
│   ├── SPEC.md
│   ├── ARCHITECTURE.md
│   ├── TESTING.md
│   ├── VERIFICATION.md
│   ├── SECURITY.md
│   ├── ROADMAP.md
│   └── adr/
│
├── implementation/                 # Vibe playbook assets, stage files, tests
│   ├── MASTER.md
│   ├── PROGRESS.md
│   ├── assets/
│   ├── stages/
│   └── tests/
│
└── tests/                          # Automated test suites
    ├── __init__.py
    ├── conftest.py                 # Pytest fixtures, test SQLite DB, respx mocks
    ├── test_catalog_fixtures.py    # Dynamic runner for all 22 catalog items
    ├── unit/                       # Component-level unit test suites
    │   ├── test_webhook_verifier.py
    │   ├── test_seller_protection.py
    │   ├── test_economics.py
    │   ├── test_sanitizer.py
    │   ├── test_evidence_compiler.py
    │   └── test_reasoning_shield.py
    ├── integration/                # Service-level integration tests
    │   ├── test_dispute_sync.py
    │   ├── test_approval_gate.py
    │   ├── test_audit_service.py
    │   └── test_api_routes.py
    └── contract/                   # PayPal API mock contract tests
        └── test_paypal_client.py
```
