# Test Strategy and Quality Gates

DisputeSentry AI enforces a strict test-driven development (TDD) methodology: **tests must be written and verified failing before implementation begins in any stage.**

---

## 1. Test Pyramid & Ground Truth Mapping

```
      / \
     /   \    Tier 4: Live Sandbox E2E Tests (PayPal Sandbox endpoints)
    /-----\
   /       \   Tier 3: Mock Contract Tests (respx / Recorded PayPal Schemas)
  /---------\
 /           \  Tier 2: Component Integration Tests (FastAPI routes, SQLite DB)
/-------------\
Tier 1: Unit & Catalog Oracle Tests (Deterministic Pure Domain Rules & Fixtures)
```

| Layer | Ground Truth Authority | Target Execution Time | Gate |
|---|---|---|---|
| **Tier 1 (Unit & Catalog)** | Catalog items (`DSP001`-`DSP022`), golden fixtures | `< 1.5 seconds` | 100% pass; 0 flaky; 90%+ line coverage |
| **Tier 2 (Integration)** | FastAPI test client, in-memory SQLite WAL | `< 1.5 seconds` | 100% pass; ACID transaction verification |
| **Tier 3 (Contract Mocks)** | Official PayPal Disputes REST API v1 OpenAPI Spec | `< 1.0 second` | Exact request header/body match |
| **Tier 4 (Sandbox E2E)** | Live PayPal Developer Sandbox | Scheduled / Pre-release | Validates end-to-end token and dispute flow |

---

## 2. Test-First Implementation Rule

Within each stage:
1. Review the corresponding `implementation/tests/S##-tests.md`.
2. Implement or verify the test functions defined in the test plan.
3. Run `pytest` to confirm tests fail with expected import or assertion errors (Red phase).
4. Implement the minimum production code in `app/` to satisfy the tests (Green phase).
5. Refactor and verify zero linter (`ruff`) or type (`mypy`) warnings.
