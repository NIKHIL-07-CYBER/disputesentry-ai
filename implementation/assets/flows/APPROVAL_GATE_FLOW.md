# Human-in-the-Loop Approval Gate and State Machine

This document defines the formal finite state machine (FSM) governing operator oversight, approval locks for financial concessions, and deadline fail-safe fallbacks.

---

## 1. State Machine Diagram

```mermaid
stateDiagram-v2
    [*] --> INGESTED
    INGESTED --> EVALUATING: Enrich with Merchant Records
    
    EVALUATING --> AUTO_READY: Amount < $100 AND Action == CONTEST AND High Confidence
    EVALUATING --> PENDING_APPROVAL: Amount >= $100 OR Action == CONCEDE OR Low Confidence
    
    PENDING_APPROVAL --> APPROVED: Operator POST /approve
    PENDING_APPROVAL --> REJECTED: Operator POST /reject
    PENDING_APPROVAL --> DISPATCHED: Fail-Safe Trigger (Time <= 2 hours)
    
    AUTO_READY --> DISPATCHED: Automated Background Dispatch
    APPROVED --> DISPATCHED: Execute Approved Mutation
    REJECTED --> RESOLVED: Operator Cancelled Action
    
    DISPATCHED --> RESOLVED: PayPal Webhook Confirms Outcome
    DISPATCHED --> ERROR_PAUSED: PayPal API Failure (Retry Budget Exhausted)
    ERROR_PAUSED --> PENDING_APPROVAL: Operator Manual Intervention
```

---

## 2. Transition Guard Rules

1. **Strict Human Gate:** A dispute with amount $\ge \$100.00$ or recommended action `CONCEDE` can NEVER transition directly to `DISPATCHED` via automated background workers, UNLESS the deadline fail-safe triggers.
2. **2-Hour Fail-Safe Emergency Rule (`DSP018`):** If a dispute remains in `PENDING_APPROVAL` with `hours_until_due <= 2.0`, the system automatically transitions state to `DISPATCHED` and uploads the assembled evidence package to avoid automatic default forfeiture by PayPal.
3. **Audit Trail Guarantee:** Every state transition must generate an append-only, SHA-256 chained entry in the audit store before acknowledging the HTTP request.
