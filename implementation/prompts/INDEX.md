# Implementation Prompts Index

This index organizes all execution and review prompts for DisputeSentry AI, establishing the strict per-stage workflow and utility tool dispatch.

Live build status is tracked in [implementation/PROGRESS.md](file:///D:/fix/challenges/paypal/implementation/PROGRESS.md).

---

## 1. Stage Execution & Review Table

| Stage ID | Stage Name | Execution Prompt | Review Prompt | Depends On | Risk |
|---|---|---|---|---|---|
| `S00` | Scaffolding and Tooling | [stages/S00-scaffolding-and-tooling-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S00-scaffolding-and-tooling-prompt.md) | [reviews/S00-scaffolding-and-tooling-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S00-scaffolding-and-tooling-review.md) | None | Low |
| `S01` | Verification Harness | [stages/S01-verification-harness-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S01-verification-harness-prompt.md) | [reviews/S01-verification-harness-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S01-verification-harness-review.md) | `S00` | Medium |
| `S02` | Webhook Ingestion Core | [stages/S02-webhook-ingestion-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S02-webhook-ingestion-prompt.md) | [reviews/S02-webhook-ingestion-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S02-webhook-ingestion-review.md) | `S01` | High |
| `S03` | Domain Models & Data Layer | [stages/S03-domain-models-and-data-layer-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S03-domain-models-and-data-layer-prompt.md) | [reviews/S03-domain-models-and-data-layer-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S03-domain-models-and-data-layer-review.md) | `S02` | High |
| `S04` | Walking Skeleton Sync | [stages/S04-walking-skeleton-paypal-sync-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S04-walking-skeleton-paypal-sync-prompt.md) | [reviews/S04-walking-skeleton-paypal-sync-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S04-walking-skeleton-paypal-sync-review.md) | `S03` | High |
| `S05` | Seller Protection Engine | [stages/S05-seller-protection-engine-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S05-seller-protection-engine-prompt.md) | [reviews/S05-seller-protection-engine-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S05-seller-protection-engine-review.md) | `S04` | Medium |
| `S06` | Economic Decision Engine | [stages/S06-economic-decision-engine-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S06-economic-decision-engine-prompt.md) | [reviews/S06-economic-decision-engine-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S06-economic-decision-engine-review.md) | `S05` | Medium |
| `S07` | Approval Gate & Fallbacks | [stages/S07-approval-gate-and-fallbacks-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S07-approval-gate-and-fallbacks-prompt.md) | [reviews/S07-approval-gate-and-fallbacks-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S07-approval-gate-and-fallbacks-review.md) | `S06` | High |
| `S08` | Evidence Attachment Compiler | [stages/S08-evidence-attachment-compiler-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S08-evidence-attachment-compiler-prompt.md) | [reviews/S08-evidence-attachment-compiler-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S08-evidence-attachment-compiler-review.md) | `S07` | Medium |
| `S09` | AI Reasoning & Shielding | [stages/S09-ai-reasoning-and-shielding-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S09-ai-reasoning-and-shielding-prompt.md) | [reviews/S09-ai-reasoning-and-shielding-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S09-ai-reasoning-and-shielding-review.md) | `S08` | High |
| `S10` | Web API & Dashboard | [stages/S10-web-api-and-dashboard-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S10-web-api-and-dashboard-prompt.md) | [reviews/S10-web-api-and-dashboard-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S10-web-api-and-dashboard-review.md) | `S09` | Low |
| `S11` | Hardening & Release | [stages/S11-hardening-and-release-prompt.md](file:///D:/fix/challenges/paypal/implementation/prompts/stages/S11-hardening-and-release-prompt.md) | [reviews/S11-hardening-and-release-review.md](file:///D:/fix/challenges/paypal/implementation/prompts/reviews/S11-hardening-and-release-review.md) | `S10` | Medium |

---

## 2. Per-Stage Execution Loop

For manual or unattended execution:
1. **Open a fresh session** with zero memory of previous sessions.
2. **Paste the stage prompt** (e.g., `implementation/prompts/stages/S00-scaffolding-and-tooling-prompt.md`).
3. **Wait for the stage Final Report** and confirm the exit criteria output is pasted.
4. **Open a separate fresh session** for the independent review.
5. **Paste the review prompt** (e.g., `implementation/prompts/reviews/S00-scaffolding-and-tooling-review.md`).
6. **Evaluate review result:**
   - If `PASS`: set status to `review-pass` in `PROGRESS.md`, tag commit (`stage-S##-pass`), and proceed.
   - If `FAIL`: dispatch `utility/blocked-triage.md` or `utility/resume.md`, re-execute review, and verify fix before proceeding.
7. Repeat for subsequent stages, or automate using [ORCHESTRATOR.md](file:///D:/fix/challenges/paypal/implementation/prompts/ORCHESTRATOR.md).

---

## 3. Utility Prompts Reference

| Utility Prompt | Path | When to Use |
|---|---|---|
| **Resume** | [utility/resume.md](file:///D:/fix/challenges/paypal/implementation/prompts/utility/resume.md) | Resuming an interrupted stage or applying a stage-local bugfix. |
| **Blocked Triage** | [utility/blocked-triage.md](file:///D:/fix/challenges/paypal/implementation/prompts/utility/blocked-triage.md) | Diagnosing an unexpected failure or test mismatch without modifying code. |
| **Spec Fix** | [utility/spec-fix.md](file:///D:/fix/challenges/paypal/implementation/prompts/utility/spec-fix.md) | Applying an approved change to catalog, SPEC, ADR, or stage specifications. |
| **Context Reset** | [utility/context-reset.md](file:///D:/fix/challenges/paypal/implementation/prompts/utility/context-reset.md) | Gracefully wrapping up a long or cluttered session before handing off. |
| **Final Acceptance** | [utility/final-acceptance.md](file:///D:/fix/challenges/paypal/implementation/prompts/utility/final-acceptance.md) | Final verification audit after S11 review-pass before releasing to judges. |

---

## 4. Strict "Never Do" Invariants

- **Never run two stages in parallel:** Stages have strict sequential dependencies.
- **Never skip a review:** Code author must never review its own implementation in the same session.
- **Never edit `catalog/` or `docs/SPEC.md` during implementation:** Propose changes via `blocked-triage.md` and execute via `spec-fix.md`.
- **Never claim success without pasted terminal output:** Exit criteria must show real command executions.
- **Never store or pass raw card numbers (PAN) or CVVs:** Enforce zero-PAN sanitization at all times.
