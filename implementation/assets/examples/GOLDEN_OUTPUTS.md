# Golden Outputs for Core Workflows

This document records the exact expected outputs for key system operations.

---

## 1. Webhook Acknowledgement Output
- HTTP Status: `200 OK`
- Content-Type: `application/json`
```json
{
  "status": "success",
  "transmission_id": "7a82c3f0-466d-11ee-be56-0242ac120002",
  "dispute_id": "PP-D-12345",
  "action": "QUEUED_FOR_EVALUATION"
}
```

---

## 2. Decision Engine Structured Output (`DisputeDecisionOutput`)
```json
{
  "recommended_action": "CONTEST",
  "win_probability": 0.92,
  "net_expected_recovery": 131.79,
  "confidence_score": 0.98,
  "seller_protection_eligible": true,
  "justification": "USPS tracking 9400100000000000000000 shows package DELIVERED to buyer postal code prior to dispute initiation.",
  "evidence_types_required": [
    "PROOF_OF_FULFILLMENT"
  ],
  "customer_text_contains_injection": false,
  "requires_human_approval": true
}
```

---

## 3. Audit Trail Entry JSON Output
```json
{
  "entry_id": "e4f801b6-a5df-4d64-88f5-93df92fa75c0",
  "timestamp": "2026-11-01T12:05:00Z",
  "dispute_id": "PP-D-12345",
  "action": "EVIDENCE_SUBMITTED",
  "actor": "SYSTEM_AI",
  "details": {
    "evidence_type": "PROOF_OF_FULFILLMENT",
    "tracking_number": "9400100000000000000000",
    "carrier": "USPS"
  },
  "prev_hash": "0000000000000000000000000000000000000000000000000000000000000000",
  "entry_hash": "a8f5b2c9d0e1f3a4b5c6d7e8f9a0b1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8"
}
```
