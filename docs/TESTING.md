# Testing Strategy and Quality Gates

## 1. Testing Philosophy
DisputeSentry AI adheres strictly to the rule:  
**No behavior merges without fixtures plus a passing oracle test.**

Every business capability, economic equation, Seller Protection rule, and API interaction must be backed by a corresponding catalog item (`DSP###`), test fixtures (`catalog/fixtures/DSP###/`), and an automated test case.

---

## 2. Testing Tiers and Tools

```
+-----------------------------------------------------------------------------------+
| Tier 4: Live PayPal Sandbox End-to-End Tests                                      |
|  - Real API calls to api-m.sandbox.paypal.com                                     |
|  - Validates end-to-end token acquisition, dispute query, and evidence submission |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Tier 3: Mock Contract Tests (respx / pytest-httpx)                                |
|  - Validates HTTP request construction, multipart encoding, and status handling   |
|  - Tests PayPal 200, 400, 401, 409, and 413 error branches                        |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Tier 2: Domain Unit & State Machine Tests                                         |
|  - 100% deterministic testing of ROI math, Seller Protection, and FSM transitions|
|  - Luhn PCI card redaction and prompt injection isolation benchmarks              |
+-----------------------------------------------------------------------------------+
                                         ^
                                         |
+-----------------------------------------------------------------------------------+
| Tier 1: Catalog Fixture Tests (pytest)                                            |
|  - Automated runner executing good.json and bad.json against expected.yaml        |
+-----------------------------------------------------------------------------------+
```

---

## 3. Coverage Gates and Quality Standards

All pull requests and stage deliverables must satisfy the following minimum gates:

| Quality Gate | Metric Threshold | Enforcement Mechanism |
|---|---|---|
| **Catalog Coverage** | 100% of `DSP###` catalog items covered | `pytest tests/test_catalog_fixtures.py` |
| **Line Coverage** | $\ge 90\%$ line coverage across `app/domain/` and `app/services/` | `pytest --cov=app --cov-fail-under=90` |
| **Type Checking** | 0 errors | `mypy --strict app/` |
| **Linting & Code Style** | 0 violations | `ruff check app/` |
| **PCI Sanitization** | 100% detection on synthetic Luhn PAN fixtures | `pytest tests/test_sanitizer.py` |

---

## 4. Test Categories

### 4.1 Catalog Fixture Runner (`tests/test_catalog_fixtures.py`)
- Automatically iterates through `catalog/fixtures/DSP*/`.
- For each directory, reads `good.json`, `bad.json`, and `expected.yaml`.
- Executes the designated domain component and asserts that the actual outcome exactly matches the expected specification.

### 4.2 Economic Formula Unit Tests (`tests/test_economics.py`)
- Tests boundary values for Expected Value calculation:
  - Low dispute amounts ($5.00) vs high fee penalties ($20.00).
  - High win probability ($0.95$) with large claims ($500.00).
  - Break-even calculations ensuring strictly positive EV before contest recommendation.

### 4.3 Seller Protection Rule Tests (`tests/test_seller_protection.py`)
- Parametric tests for INR, Unauthorised, and SNAD dispute reasons.
- Verifies edge cases: delivery to neighboring zip codes, carrier tracking missing timestamps, packages delivered post-dispute creation.

### 4.4 PCI DSS Redaction & Security Tests (`tests/test_sanitizer.py`)
- Generates valid card numbers for Visa, Mastercard, and Amex using the Luhn algorithm.
- Injects card numbers into realistic dispute narratives and verifies that all numbers are masked to `[REDACTED_PAN]`.

### 4.5 PayPal API Contract Tests (`tests/test_paypal_client.py`)
- Uses `respx` to mock PayPal REST API endpoints.
- Tests token expiration and automatic refresh replay on 401 Unauthorized.
- Tests multipart boundary generation and attachment validation.

---

## 5. Flake Elimination Policy

1. **No External Network in Tiers 1-3**:
   - Tiers 1, 2, and 3 must never attempt outbound network calls. Any external HTTP request triggers a socket block and fails the test.
2. **Deterministic Time Injection**:
   - All tests asserting time-based rules (`seller_response_due_date`, deadline warnings) inject a frozen timestamp via test parameters.
3. **Isolated Test Databases**:
   - Each test function runs against an in-memory SQLite database (`sqlite:///:memory:`) initialized with fresh migrations.
