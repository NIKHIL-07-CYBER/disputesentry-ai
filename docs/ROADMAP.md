# Build Roadmap (B-Checkpoints)

This roadmap defines the sequential build checkpoints for DisputeSentry AI. Each checkpoint is a standalone task with explicit entry and exit criteria. The subsequent implementation playbook phase (`vibe-2-playbook`) decomposes these checkpoints into executable stage files.

---

## Checkpoint Overview

```
+-----------------------------------------------------------------------------------+
| B-1: Project Scaffolding & Environment Setup                                      |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-2: Verification Test Harness & Fixture Runner                                   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-3: Ingestion & Webhook Cryptographic Verification Core (DSP001 - DSP004)        |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-4: Domain Models & Merchant Data Layer (DSP006, DSP019, DSP022)                 |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-5: First End-to-End Slice: PayPal Client & Dispute Sync (DSP005, DSP010, DSP014)|
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-6: Seller Protection Rule Engine (DSP007, DSP008, DSP009)                       |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-7: Economic Decision & Net Recovery ROI Engine (DSP011, DSP012, DSP021)         |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-8: Human-in-the-Loop Approval Gate & Safe Fallbacks (DSP013, DSP015, DSP018)    |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-9: Evidence Attachment Compiler & Validation (DSP016, DSP017)                   |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-10: AI Reasoning Shielding & Prompt Injection Defense (DSP020)                  |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-11: Web API & Merchant Operator Dashboard                                       |
+------------------------------------------+----------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------+
| B-12: System Hardening, Sandbox End-to-End Validation & Release                   |
+-----------------------------------------------------------------------------------+
```

---

## Detailed Checkpoint Specifications

### B-1: Project Scaffolding & Environment Setup
- **Depends on**: `docs/adr/ADR-001-language-and-stack.md`, `docs/ARCHITECTURE.md`
- **Scope**: Initialize project root files (`pyproject.toml`, `requirements.txt`, `.gitignore`, `config.yaml`), directory structure (`app/`, `tests/`), and virtualenv verification script.
- **Entry condition**: Foundation phase documents complete and verified.
- **Exit condition**: `pytest` and `ruff check` run without configuration errors in clean virtual environment.

### B-2: Verification Test Harness & Fixture Runner
- **Depends on**: `docs/VERIFICATION.md`, `catalog/_schema.json`, `catalog/fixtures/`
- **Scope**: Build automated fixture runner (`tests/test_catalog_fixtures.py`) that loads all 22 catalog item fixtures (`good.json`, `bad.json`) and compares execution outputs against `expected.yaml`.
- **Entry condition**: B-1 complete.
- **Exit condition**: Fixture runner discovers all 22 fixture directories and reports expected assertion results for dummy mock targets.

### B-3: Ingestion & Webhook Cryptographic Verification Core
- **Depends on**: `catalog/DSP001.yaml` through `catalog/DSP004.yaml`, `docs/SPEC.md` §4.2.1, `docs/SECURITY.md`
- **Scope**: Implement `app/clients/webhook_verifier.py` and `POST /webhooks/paypal` endpoint. Supports X.509 cert fetching with PayPal domain whitelist (`DSP004`), RSA-SHA256 signature verification (`DSP001`, `DSP002`), and deduplication (`DSP003`).
- **Entry condition**: B-2 complete.
- **Exit condition**: Fixtures `DSP001`, `DSP002`, `DSP003`, and `DSP004` pass 100% in test runner.

### B-4: Domain Models & Merchant Data Layer
- **Depends on**: `catalog/DSP006.yaml`, `catalog/DSP019.yaml`, `catalog/DSP022.yaml`, `docs/ARCHITECTURE.md` §2
- **Scope**: Implement core domain models (`Dispute`, `EvidencePackage`, `OrderRecord`), PCI DSS PAN/CVV regex scrubber (`DSP019`), SQLite schema with WAL mode, seeded merchant order database (`DSP006`), and tamper-evident append-only audit trail with SHA-256 state hashing (`DSP022`).
- **Entry condition**: B-3 complete.
- **Exit condition**: Fixtures `DSP006`, `DSP019`, and `DSP022` pass 100%; seeded database returns known order and tracking records.

### B-5: First End-to-End Slice: PayPal Client & Dispute Sync
- **Depends on**: `catalog/DSP005.yaml`, `catalog/DSP010.yaml`, `catalog/DSP014.yaml`, `docs/adr/ADR-002-integration-strategy.md`
- **Scope**: Implement `app/clients/paypal_client.py` with OAuth 2.0 token caching and automatic refresh; `GET /v1/customer/disputes/{id}`; response due date urgency parser (`DSP010`); allowed HATEOAS link validator (`DSP005`); basic evidence submission dispatch (`DSP014`).
- **Entry condition**: B-4 complete.
- **Exit condition**: Fixtures `DSP005`, `DSP010`, and `DSP014` pass 100% against `respx` mock contracts.

### B-6: Seller Protection Rule Engine
- **Depends on**: `catalog/DSP007.yaml`, `catalog/DSP008.yaml`, `catalog/DSP009.yaml`, `docs/CATALOG.md` §2
- **Scope**: Implement `app/domain/seller_protection.py`. Deterministic rule evaluations for:
  - `MERCHANDISE_OR_SERVICE_NOT_RECEIVED` delivery verification (`DSP007`).
  - `UNAUTHORISED` shipment date prior to notification (`DSP008`).
  - `MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED` refund/policy matching (`DSP009`).
- **Entry condition**: B-5 complete.
- **Exit condition**: Fixtures `DSP007`, `DSP008`, and `DSP009` pass 100% with parametric edge-case tests.

### B-7: Economic Decision & Net Recovery ROI Engine
- **Depends on**: `catalog/DSP011.yaml`, `catalog/DSP012.yaml`, `catalog/DSP021.yaml`, `docs/SPEC.md` §3
- **Scope**: Implement `app/domain/economics.py` and `app/services/audit_service.py`. Computes Net Expected Recovery formula ($\text{EV} = P_{\text{win}} \cdot \text{Amount} - (1-P_{\text{win}}) \cdot \text{Fee} - \text{Overhead}$) recommending contest vs concede (`DSP011`). Implements inquiry messaging (`DSP012`) and recovery metrics (`DSP021`).
- **Entry condition**: B-6 complete.
- **Exit condition**: Fixtures `DSP011`, `DSP012`, and `DSP021` pass 100%; metrics endpoint returns accurate win rate and net recovery calculations.

### B-8: Human-in-the-Loop Approval Gate & Safe Fallbacks
- **Depends on**: `catalog/DSP013.yaml`, `catalog/DSP015.yaml`, `catalog/DSP018.yaml`, `docs/SPEC.md` §4.2.2
- **Scope**: Implement `app/services/approval_gate.py`. Intercepts disputes with amount $\ge \$100$ or low confidence into `PENDING_APPROVAL` (`DSP013`). Implements `/approve` and `/reject` APIs; executes `accept-claim` API for concessions (`DSP015`); implements deadline monitor triggering auto-defense within 2 hours of due date (`DSP018`).
- **Entry condition**: B-7 complete.
- **Exit condition**: Fixtures `DSP013`, `DSP015`, and `DSP018` pass 100%; state machine transitions accurately enforce operator approval locks.

### B-9: Evidence Attachment Compiler & Validation
- **Depends on**: `catalog/DSP016.yaml`, `catalog/DSP017.yaml`, `docs/adr/ADR-002-integration-strategy.md`
- **Scope**: Implement evidence file packaging. Validates file sizes (max 10 MB per file, max 50 MB total) (`DSP016`) and MIME types (JPG, PNG, PDF) (`DSP017`). Encodes multipart/form-data payload with `input` JSON part and binary attachment parts for PayPal API.
- **Entry condition**: B-8 complete.
- **Exit condition**: Fixtures `DSP016` and `DSP017` pass 100%; multipart payload matches PayPal specification.

### B-10: AI Reasoning Shielding & Prompt Injection Defense
- **Depends on**: `catalog/DSP020.yaml`, `docs/SECURITY.md` §1, `app/clients/ai_client.py`
- **Scope**: Implement structured Gemini decision engine with Pydantic output constraints (`DisputeDecisionOutput`). Wraps untrusted customer notes in XML boundaries and applies system prompt shielding to neutralize prompt injection overrides (`DSP020`).
- **Entry condition**: B-9 complete.
- **Exit condition**: Fixture `DSP020` passes 100%; adversarial prompt tests demonstrate 0% override success rate.

### B-11: Web API & Merchant Operator Dashboard
- **Depends on**: `docs/SPEC.md` §4.2, `docs/ARCHITECTURE.md` §2
- **Scope**: Implement FastAPI web dashboard using Jinja2 templates. Real-time dispute queue sorted by `seller_response_due_date` and amount; one-click Approve/Reject buttons; dispute detail modal with evidence inspection and audit trail log viewer.
- **Entry condition**: B-10 complete.
- **Exit condition**: Dashboard renders responsive UI in browser; user can inspect dispute and execute approval action in local test mode.

### B-12: System Hardening, Sandbox End-to-End Validation & Release
- **Depends on**: `docs/CI_RELEASE.md`, `docs/VERIFICATION.md`, `PROBLEM_STATEMENT.md` §11
- **Scope**: Execute full PayPal Sandbox test suite with real test transactions across all three primary dispute reasons (INR, Unauthorised, SNAD). Validate Docker container build and write `README.md` with judge run instructions.
- **Entry condition**: B-11 complete.
- **Exit condition**: 100% catalog items verified; Docker image boots and serves dashboard; demo video recording checklist verified.
