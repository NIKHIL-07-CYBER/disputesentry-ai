# AGENTS.md
Project: DisputeSentry AI. Automated PayPal dispute detection, evidence assembly, ROI evaluation, and API resolution.

## Before coding
- Read [docs/SPEC.md](file:///D:/fix/challenges/paypal/docs/SPEC.md), [docs/ARCHITECTURE.md](file:///D:/fix/challenges/paypal/docs/ARCHITECTURE.md), and the catalog items in [catalog/](file:///D:/fix/challenges/paypal/catalog/) for your specific task.
- If `implementation/MASTER.md` exists, follow its routing instead of bulk-reading the repository.
- Verify your environment matches [docs/adr/ADR-001-language-and-stack.md](file:///D:/fix/challenges/paypal/docs/adr/ADR-001-language-and-stack.md).

## Non-negotiables
- Unit of progress = catalog item + fixtures + passing oracle test. Never ship behavior without all three.
- Never claim domain behavior that is not in the catalog. If you need one, log it in [docs/OPEN_QUESTIONS.md](file:///D:/fix/challenges/paypal/docs/OPEN_QUESTIONS.md) and stop.
- Never edit [catalog/](file:///D:/fix/challenges/paypal/catalog/), [docs/SPEC.md](file:///D:/fix/challenges/paypal/docs/SPEC.md), or ADRs from an implementation task. Propose the change instead.
- Small diffs. One commit per checkpoint. Stop if a precondition is unmet.
- Run lint, type-check, and the full test suite before finishing. Paste real terminal output; never claim success without it.
- When a spec is ambiguous, stop and ask; do not guess.
- Record non-obvious architecture decisions as ADRs in `docs/adr/`.
- Strict zero-PAN rule: Never log, store, or pass credit card numbers (PAN) or CVV codes to LLM prompts. Use the sanitizer in [docs/SECURITY.md](file:///D:/fix/challenges/paypal/docs/SECURITY.md).
- Strict human gate: Never auto-execute concessions or actions on disputes >= $100 without explicit operator approval.

## Where things live
| Topic | Path |
|---|---|
| Problem Statement | [PROBLEM_STATEMENT.md](file:///D:/fix/challenges/paypal/PROBLEM_STATEMENT.md) |
| Open Questions & Assumptions | [docs/OPEN_QUESTIONS.md](file:///D:/fix/challenges/paypal/docs/OPEN_QUESTIONS.md) |
| Competitor Research | [docs/research/competitors.md](file:///D:/fix/challenges/paypal/docs/research/competitors.md) |
| Stack Selection (ADR-001) | [docs/adr/ADR-001-language-and-stack.md](file:///D:/fix/challenges/paypal/docs/adr/ADR-001-language-and-stack.md) |
| Integration Strategy (ADR-002) | [docs/adr/ADR-002-integration-strategy.md](file:///D:/fix/challenges/paypal/docs/adr/ADR-002-integration-strategy.md) |
| Scope & Version Policy (ADR-003) | [docs/adr/ADR-003-scope-and-versions.md](file:///D:/fix/challenges/paypal/docs/adr/ADR-003-scope-and-versions.md) |
| Verification Strategy (ADR-004) | [docs/adr/ADR-004-verification-strategy.md](file:///D:/fix/challenges/paypal/docs/adr/ADR-004-verification-strategy.md) |
| Product Specification | [docs/SPEC.md](file:///D:/fix/challenges/paypal/docs/SPEC.md) |
| Master Behavior Catalog | [docs/CATALOG.md](file:///D:/fix/challenges/paypal/docs/CATALOG.md) |
| Catalog Item Schema | [catalog/_schema.json](file:///D:/fix/challenges/paypal/catalog/_schema.json) |
| Behavior Fixtures | [catalog/fixtures/](file:///D:/fix/challenges/paypal/catalog/fixtures/) |
| Verification Protocol | [docs/VERIFICATION.md](file:///D:/fix/challenges/paypal/docs/VERIFICATION.md) |
| Architecture & Boundaries | [docs/ARCHITECTURE.md](file:///D:/fix/challenges/paypal/docs/ARCHITECTURE.md) |
| Testing Standards & Gates | [docs/TESTING.md](file:///D:/fix/challenges/paypal/docs/TESTING.md) |
| Security Model & Threat Rules | [docs/SECURITY.md](file:///D:/fix/challenges/paypal/docs/SECURITY.md) |
| CI/CD & Release Design | [docs/CI_RELEASE.md](file:///D:/fix/challenges/paypal/docs/CI_RELEASE.md) |
| Build Roadmap (B-Checkpoints) | [docs/ROADMAP.md](file:///D:/fix/challenges/paypal/docs/ROADMAP.md) |
| Foundation Audit Report | [docs/FOUNDATION_REPORT.md](file:///D:/fix/challenges/paypal/docs/FOUNDATION_REPORT.md) |
| Implementation Master Router | [implementation/MASTER.md](file:///D:/fix/challenges/paypal/implementation/MASTER.md) |

## Definition of Done
- [ ] Catalog items covered have fixtures and passing oracle tests per [docs/VERIFICATION.md](file:///D:/fix/challenges/paypal/docs/VERIFICATION.md).
- [ ] Lint (`ruff`), type-check (`mypy`), and unit tests (`pytest`) are 100% green.
- [ ] No files touched outside the stage allowlist.
- [ ] Docs unchanged unless the task was explicitly a spec-fix.
- [ ] Progress tracker updated in `implementation/PROGRESS.md`.
