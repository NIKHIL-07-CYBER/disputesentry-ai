# CI Matrix Specification

This document defines the continuous integration matrix and build verification gates.

---

## 1. Environments & Toolchains

| OS / Target | Python Version | Tooling Target | Required Checks |
|---|---|---|---|
| Ubuntu 22.04 LTS / Windows | Python 3.11 | Standard virtualenv | `ruff check .`, `mypy --strict app/`, `pytest` |
| Ubuntu 22.04 LTS | Python 3.12 | Forward compatibility | `pytest` |
| Container (Alpine / Debian Slim) | Python 3.11 | Docker Build | Container image boots and responds to `/health` |

---

## 2. Gate Definitions

- **Lint Gate:** `ruff check app/ tests/` (0 warnings allowed).
- **Type Check Gate:** `mypy --strict app/` (0 type errors allowed).
- **Test Gate:** `pytest --maxfail=1 tests/` (100% pass; 0 skipped; 0 failures).
- **Performance Gate:** Full offline test suite must complete in $< 5.0\text{ seconds}$.
