# Golden Files Policy and Review Rules

This document specifies the storage layout, update policy, and review rules for golden test fixtures.

---

## 1. Golden Files Storage

Golden files reside exclusively in:
- `catalog/fixtures/DSP###/expected.yaml`
- `implementation/assets/examples/GOLDEN_OUTPUTS.md`

---

## 2. Update and Mutation Rules

1. **Strict Immutability during Implementation:**
   - Golden fixture files under `catalog/fixtures/` must NEVER be modified by an implementation stage prompt.
   - If a test fails against a golden file, the implementation code must be corrected to match the golden contract.
2. **Spec-Fix Protocol for Intentional Schema Changes:**
   - If an official PayPal API update invalidates a golden fixture, the change must be proposed, approved, recorded in `docs/OPEN_QUESTIONS.md`, and merged as a distinct `spec-fix` commit.
