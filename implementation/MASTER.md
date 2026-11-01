# MASTER: Implementation Router

## Purpose
This router enables coding agents in fresh sessions to execute any stage of DisputeSentry AI by reading only the minimal files required, preventing context window bloat and eliminating ambiguity.

## Folder Map
- `implementation/stages/`: Per-stage executable instructions (`S00-*.md` to `S11-*.md`).
- `implementation/tests/`: Per-stage test specs (`S00-tests.md` to `S11-tests.md`) and cross-cutting test strategy.
- `implementation/assets/`: System architecture, domain models, sequence flows, and reference matrices.
- `implementation/prompts/`: Stage execution and review prompts, orchestrator, and utility tools (see `prompts/INDEX.md`).
- `catalog/fixtures/`: Golden test fixtures for all 22 behavioral catalog items (`DSP001` - `DSP022`).

## Global Invariants
- **Unit of progress:** Catalog item + fixtures + passing oracle test. Never ship behavior without all three.
- **Strict zero-PAN rule:** Never log, store, or pass unmasked card numbers (Luhn-valid) or CVVs to LLMs or disk.
- **Strict human gate:** Disputes $\ge \$100$ or concessions require explicit operator approval.
- **Deterministic CI:** All unit/integration tests run offline in $< 5.0\text{ seconds}$ with zero network dependencies.

## Context-Loading Protocol
Load **only** the files specified for your assigned stage. Do not bulk-read the repository.

## Stage Routing Table

| Stage | Stage File | Tests File | Assets to Read | Catalog IDs / Scope | Depends On |
|---|---|---|---|---|---|
| `S00` | `stages/S00-scaffolding-and-tooling.md` | `tests/S00-tests.md` | `assets/architecture/REPO_LAYOUT.md`, `DEPENDENCIES.md` | Scaffolding, config, health check | None |
| `S01` | `stages/S01-verification-harness.md` | `tests/S01-tests.md` | `tests/FIXTURE_CONVENTIONS.md`, `ITEM_TEST_RECIPE.md` | Fixture runner harness | `S00` |
| `S02` | `stages/S02-webhook-ingestion.md` | `tests/S02-tests.md` | `assets/flows/WEBHOOK_INGESTION_FLOW.md` | `DSP001`, `DSP002`, `DSP003`, `DSP004` | `S01` |
| `S03` | `stages/S03-domain-models-and-data-layer.md` | `tests/S03-tests.md` | `assets/data-models/CORE_TYPES.md` | `DSP006`, `DSP019`, `DSP022` | `S02` |
| `S04` | `stages/S04-walking-skeleton-paypal-sync.md` | `tests/S04-tests.md` | `assets/flows/DISPUTE_SYNC_FLOW.md`, `PAYPAL_API_MATRIX.md` | `DSP005`, `DSP010`, `DSP014` | `S03` |
| `S05` | `stages/S05-seller-protection-engine.md` | `tests/S05-tests.md` | `assets/reference/SELLER_PROTECTION_MATRIX.md` | `DSP007`, `DSP008`, `DSP009` | `S04` |
| `S06` | `stages/S06-economic-decision-engine.md` | `tests/S06-tests.md` | `assets/flows/EVALUATION_AND_DECISION_FLOW.md` | `DSP011`, `DSP012`, `DSP021` | `S05` |
| `S07` | `stages/S07-approval-gate-and-fallbacks.md` | `tests/S07-tests.md` | `assets/flows/APPROVAL_GATE_FLOW.md` | `DSP013`, `DSP015`, `DSP018` | `S06` |
| `S08` | `stages/S08-evidence-attachment-compiler.md` | `tests/S08-tests.md` | `assets/flows/EVIDENCE_COMPILATION_FLOW.md` | `DSP016`, `DSP017` | `S07` |
| `S09` | `stages/S09-ai-reasoning-and-shielding.md` | `tests/S09-tests.md` | `assets/flows/AI_REASONING_FLOW.md` | `DSP020` | `S08` |
| `S10` | `stages/S10-web-api-and-dashboard.md` | `tests/S10-tests.md` | `assets/architecture/REPO_LAYOUT.md` | Web operator UI & routes | `S09` |
| `S11` | `stages/S11-hardening-and-release.md` | `tests/S11-tests.md` | `docs/CI_RELEASE.md`, `docs/VERIFICATION.md` | Docker, sandbox eval, README | `S10` |

## Task-Type Routing Table

| Task | Read These |
|---|---|
| Implementing catalog item | Catalog YAML in `catalog/`, fixture in `catalog/fixtures/`, stage file in `stages/` |
| Modifying data structures | `assets/data-models/CORE_TYPES.md`, then update `app/domain/models.py` |
| Debugging test failure | Corresponding `tests/S##-tests.md`, `tests/FLAKE_POLICY.md` |
| Spec discrepancy found | Stop immediately. Follow Spec Change Protocol below. |

## Protocols

### Starting a Stage
1. Verify predecessor stage shows `review-pass` in `implementation/PROGRESS.md`.
2. Read the assigned stage file and tests file from the Stage Routing Table above.
3. Verify entry conditions. Write/enable stage tests first (ensure Red status).

### Finishing a Stage
1. Verify all unit tests, catalog oracle tests, linter (`ruff`), and type-checker (`mypy`) are green.
2. Verify diff touches only files listed in Section 4 of the stage file.
3. Commit using the exact commit message from Section 12.
4. Update `implementation/PROGRESS.md` to `implemented`.

### Spec Change Protocol
If a foundation spec, catalog item, or ADR appears incorrect or incomplete:
1. Stop implementation immediately. Do NOT guess or modify spec files.
2. Log the discrepancy in `docs/OPEN_QUESTIONS.md`.
3. Mark current stage as `blocked` in `implementation/PROGRESS.md`.
4. Request operator guidance or execute an explicit `spec-fix` review.

## Kickoff
To execute any stage, invoke:
`Execute stage S## following implementation/MASTER.md`
