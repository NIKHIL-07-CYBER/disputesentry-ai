# Package Boundaries and Dependency Rules

This document establishes the architectural layering and permitted import directions for DisputeSentry AI. Adherence to these boundaries prevents circular dependencies and isolates pure domain logic from framework and network concerns.

---

## 1. Architectural Layers

```
Layer 4: Delivery & Presentation (app/api, app/templates, app/main.py)
   |
   v
Layer 3: Services & Application Workflows (app/services)
   |
   v
Layer 2: External Clients & Storage Adapters (app/clients, app/storage)
   |
   v
Layer 1: Pure Domain Layer & Models (app/domain, app/models)
```

---

## 2. Permitted Import Rules

| Source Package | Permitted Imports | Prohibited Imports |
|---|---|---|
| `app/domain` | Standard library, `pydantic` | `app/api`, `app/services`, `app/clients`, `app/storage`, `fastapi`, `httpx` |
| `app/models` | Standard library, `pydantic` | `app/api`, `app/services`, `app/clients`, `app/storage`, `fastapi` |
| `app/storage` | `app/domain`, `app/models`, `aiosqlite`, standard library | `app/api`, `app/services`, `app/clients`, `fastapi` |
| `app/clients` | `app/domain`, `app/models`, `httpx`, `cryptography`, standard library | `app/api`, `app/services`, `fastapi` |
| `app/services` | `app/domain`, `app/models`, `app/clients`, `app/storage`, standard library | `app/api`, `fastapi` (services must remain transport-agnostic) |
| `app/api` | `app/services`, `app/domain`, `app/models`, `fastapi`, `jinja2` | Direct database manipulation bypassing `app/services` or `app/storage` |

---

## 3. Strict Boundary Invariants

1. **Pure Domain Independence:**
   - Code inside `app/domain` must have zero network I/O and zero database calls. Calculations (`economics.py`, `seller_protection.py`) must be pure deterministic functions or methods operating strictly on in-memory domain objects.
2. **PCI Sanitization at Boundaries:**
   - Data entering the system via `app/api` or `app/clients` must pass through `app/services/sanitizer.py` before being stored in `app/storage` or passed to `app/clients/ai_client.py`.
3. **No Framework Leaks:**
   - Domain objects must never import or inherit from FastAPI request or response objects. Pydantic models in `app/domain/models.py` serve as the universal internal representation.
