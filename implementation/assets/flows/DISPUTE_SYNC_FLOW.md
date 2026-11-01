# Dispute Synchronization and Walking Skeleton Flow

This document details the lifecycle of an ingested dispute, from initial webhook trigger through merchant record linking, HATEOAS verification, and response urgency tracking.

---

## 1. Flow Diagram

```mermaid
flowchart TD
    A[Inbound Verified Webhook Event] --> B{Event Type?}
    B -->|CUSTOMER.DISPUTE.CREATED| C[Fetch Dispute Details via GET /v1/customer/disputes/id]
    B -->|CUSTOMER.DISPUTE.UPDATED| C
    B -->|CUSTOMER.DISPUTE.RESOLVED| R[Update Status to RESOLVED; Record Metrics]
    
    C --> D[Extract Transaction ID & Invoice Number]
    D --> E[Query Local SQLite Merchant Store]
    
    E --> F{Order Record Found?}
    F -->|Yes| G[Assemble MerchantEvidencePackage]
    F -->|No| H[Flag Dispute as UNMATCHED_ORDER; Alert Operator]
    
    G --> I[Parse seller_response_due_date]
    I --> J[Calculate hours_until_due & Urgency Tier]
    
    J --> K[Inspect dispute.links Array for HATEOAS Actions]
    K --> L{provide_evidence link present?}
    L -->|Yes| M[Mark Ready for Domain Engine / S04 Walking Skeleton]
    L -->|No| N[Log Link Restriction; Lock Mutation Actions]
```

---

## 2. Urgency Tiers based on `seller_response_due_date`

| Time Remaining (`hours_until_due`) | Urgency Classification | System Behavior |
|---|---|---|
| `> 72 hours` | `LOW` | Normal evaluation queue; human review window open. |
| `24 to 72 hours` | `MEDIUM` | Visual warning on dashboard; highlighted in review queue. |
| `2 to 24 hours` | `CRITICAL` | Operator alert; prioritized at top of approval list. |
| `≤ 2 hours` | `FAIL_SAFE_EMERGENCY` | Auto-dispatch defensive evidence package to prevent default forfeiture. |
