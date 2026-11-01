# Core Domain Types and Data Models

This document defines the core Pydantic v2 domain models used across DisputeSentry AI. All models enforce strict type validation, field constraints, and PCI DSS sanitization invariants.

---

## 1. Domain Enumerations

```python
from enum import Enum

class DisputeReason(str, Enum):
    MERCHANDISE_OR_SERVICE_NOT_RECEIVED = "MERCHANDISE_OR_SERVICE_NOT_RECEIVED"
    MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED = "MERCHANDISE_OR_SERVICE_NOT_AS_DESCRIBED"
    UNAUTHORISED = "UNAUTHORISED"
    CREDIT_NOT_PROCESSED = "CREDIT_NOT_PROCESSED"
    OTHER = "OTHER"

class DisputeStatus(str, Enum):
    OPEN = "OPEN"
    WAITING_FOR_SELLER_RESPONSE = "WAITING_FOR_SELLER_RESPONSE"
    WAITING_FOR_BUYER_RESPONSE = "WAITING_FOR_BUYER_RESPONSE"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"

class DisputeLifeCycleStage(str, Enum):
    INQUIRY = "INQUIRY"
    CHARGEBACK = "CHARGEBACK"
    PRE_ARBITRATION = "PRE_ARBITRATION"
    ARBITRATION = "ARBITRATION"

class InternalState(str, Enum):
    INGESTED = "INGESTED"
    EVALUATING = "EVALUATING"
    AUTO_READY = "AUTO_READY"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    DISPATCHED = "DISPATCHED"
    RESOLVED = "RESOLVED"
    ERROR_PAUSED = "ERROR_PAUSED"

class RecommendedAction(str, Enum):
    CONTEST = "CONTEST"
    CONCEDE = "CONCEDE"
    INQUIRY_OFFER = "INQUIRY_OFFER"
    SEND_MESSAGE = "SEND_MESSAGE"
    ESCALATE = "ESCALATE"

class ProtectionEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    PARTIALLY_ELIGIBLE = "PARTIALLY_ELIGIBLE"
    INELIGIBLE = "INELIGIBLE"
```

---

## 2. Pydantic Core Models

### `Money`
- **Fields:** `currency: str` (3-letter ISO code, e.g. "USD"), `value: float` (must be $\ge 0.0$).
- **Invariants:** `value` cannot be negative. Formats as two decimal places on serialization.
- **Example:** `Money(currency="USD", value=149.99)`

### `MerchantOrderRecord`
- **Fields:**
  - `order_id: str`
  - `transaction_id: str`
  - `buyer_email: str`
  - `shipping_address: dict[str, str]` (keys: `line1`, `city`, `state`, `postal_code`, `country_code`)
  - `carrier: str` (e.g., "USPS", "UPS", "FEDEX", "DHL")
  - `tracking_number: str`
  - `delivery_status: str` (e.g., "DELIVERED", "IN_TRANSIT", "SHIPPED")
  - `shipped_date: str` (ISO 8601 string)
  - `delivery_date: str | None` (ISO 8601 string)
  - `refund_history: list[dict[str, str | float]]`
- **Invariants:** `buyer_email` and `tracking_number` must be non-empty strings. `shipping_address` must contain at least `country_code` and `postal_code`.

### `DisputeRecord`
- **Fields:**
  - `dispute_id: str` (e.g., `PP-D-12345`)
  - `create_time: str` (ISO 8601)
  - `reason: DisputeReason`
  - `status: DisputeStatus`
  - `dispute_life_cycle_stage: DisputeLifeCycleStage`
  - `dispute_amount: Money`
  - `seller_response_due_date: str` (ISO 8601)
  - `hours_until_due: float`
  - `allowed_links: list[str]` (HATEOAS action names, e.g. `["provide-evidence", "accept-claim"]`)
  - `internal_state: InternalState`
  - `recommended_action: RecommendedAction | None`
  - `win_probability: float` (0.0 to 1.0)
  - `expected_recovery: float`
  - `assigned_operator: str | None`
  - `customer_notes: str`
- **Invariants:** `hours_until_due` is computed dynamically. `internal_state` must be `PENDING_APPROVAL` if `dispute_amount.value >= 100.00` and `recommended_action == RecommendedAction.CONCEDE`.

### `AuditTrailEntry`
- **Fields:**
  - `entry_id: str` (UUID4)
  - `timestamp: str` (ISO 8601)
  - `dispute_id: str`
  - `action: str`
  - `actor: str` ("SYSTEM_AI", "OPERATOR_HUMAN", "FALLBACK_DAEMON")
  - `details: dict[str, Any]` (JSON payload scrubbed of PAN/PII)
  - `prev_hash: str` (Hex SHA-256 of previous audit record)
  - `entry_hash: str` (Hex SHA-256 of current record data + prev_hash)
- **Invariants:** Forms an immutable cryptographically linked audit chain per dispute.

---

## 3. Serialization & Zero-Value Conventions

- Default float values for financial amounts default to `0.0`.
- Missing timestamps default to current UTC ISO 8601 string.
- Strings scrubbed of card numbers retain prefix/suffix: `4111-XXXX-XXXX-1111`.
