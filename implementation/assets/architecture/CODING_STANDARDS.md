# Coding Standards and Style Guide

This document defines the code quality and engineering standards enforced across all implementation stages of DisputeSentry AI.

---

## 1. Toolchain & Linter Configuration

- **Formatter & Linter:** `ruff` with line length 100.
- **Type Checker:** `mypy --strict` targeting Python 3.11+. Every function and method signature must have explicit argument types and return type annotations.
- **Naming Conventions:**
  - Modules & packages: `snake_case` (e.g., `webhook_verifier.py`, `dispute_sync.py`).
  - Classes & Pydantic models: `PascalCase` (e.g., `DisputeRecord`, `SellerProtectionResult`).
  - Functions & methods: `snake_case` (e.g., `verify_signature`, `calculate_expected_recovery`).
  - Constants & enums: `UPPER_SNAKE_CASE` (e.g., `MAX_ATTACHMENT_SIZE_BYTES`, `DisputeStage.CHARGEBACK`).

---

## 2. Error Handling & Exceptions

1. **Domain-Specific Hierarchy:**
   - All custom exceptions derive from `DisputeSentryError` located in `app.domain.exceptions`.
   - Never raise generic `Exception` or return untyped string error dictionaries.
2. **Explicit Fallbacks:**
   - Network or LLM failures must be caught explicitly and routed to deterministic heuristic rules or operator approval gates.
   - Unhandled exceptions in background workers must log structured context (excluding PAN/PII) and transition dispute state to `ERROR_PAUSED`.

```python
class DisputeSentryError(Exception):
    """Base exception for all domain and operational failures."""

class SignatureVerificationError(DisputeSentryError):
    """Raised when webhook cryptographic signature fails verification."""

class HATEOASViolationError(DisputeSentryError):
    """Raised when an API action is attempted without the required link."""
```

---

## 3. Logging & Zero-PAN Security Rule

1. **Structured Logging:**
   - Use standard library `logging` configured for JSON or formatted key-value pairs.
   - Always include `dispute_id` and `action` in log records where available.
2. **Strict Zero-PAN Compliance (PCI DSS 3.4):**
   - **Never** log, persist, or pass full Primary Account Numbers (13-19 digits matching Luhn) or CVV codes (3-4 digits).
   - Log formatters and data persistence pipelines must execute regex masking (`4111-XXXX-XXXX-1111`) before writing to disk or terminal.

---

## 4. Async & Concurrency Standards

- Prefer `async`/`await` for all I/O bound operations (database calls via `aiosqlite`, HTTP requests via `httpx`).
- Pure CPU calculations (`economics.py`, `seller_protection.py`) must be synchronous to avoid event loop thread overhead.
- Database transactions must use async context managers: `async with db.transaction(): ...`.
