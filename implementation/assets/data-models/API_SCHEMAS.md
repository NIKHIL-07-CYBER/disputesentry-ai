# API Schemas and Wire Contracts

This document specifies the inbound and outbound wire schemas for DisputeSentry AI REST endpoints, PayPal API v1 interactions, and AI model outputs.

---

## 1. Webhook Ingestion Schema (`POST /webhooks/paypal`)

### Inbound Headers
```http
POST /webhooks/paypal HTTP/1.1
Host: example.com
Content-Type: application/json
PAYPAL-AUTH-ALGO: SHA256withRSA
PAYPAL-CERT-URL: https://api.sandbox.paypal.com/v1/notifications/certs/CERT-123.pem
PAYPAL-TRANSMISSION-ID: 7a82c3f0-466d-11ee-be56-0242ac120002
PAYPAL-TRANSMISSION-SIG: MEUCIQDx...==
PAYPAL-TRANSMISSION-TIME: 2026-11-01T10:00:00Z
```

### Inbound Webhook Event Body
```json
{
  "id": "WH-90812371",
  "event_version": "1.0",
  "create_time": "2026-11-01T10:00:00Z",
  "resource_type": "dispute",
  "event_type": "CUSTOMER.DISPUTE.CREATED",
  "summary": "Dispute created for order 1001",
  "resource": {
    "dispute_id": "PP-D-12345",
    "create_time": "2026-11-01T09:59:00Z",
    "dispute_amount": {
      "currency": "USD",
      "value": "149.99"
    },
    "reason": "MERCHANDISE_OR_SERVICE_NOT_RECEIVED",
    "status": "WAITING_FOR_SELLER_RESPONSE",
    "dispute_life_cycle_stage": "CHARGEBACK",
    "seller_response_due_date": "2026-11-11T10:00:00Z",
    "disputed_transactions": [
      {
        "seller_transaction_id": "TX-998811",
        "buyer_transaction_id": "TX-BUYER-11",
        "invoice_number": "INV-1001"
      }
    ],
    "messages": [
      {
        "posted_by": "BUYER",
        "time_posted": "2026-11-01T09:59:00Z",
        "content": "Package was never delivered to my front door."
      }
    ],
    "links": [
      {
        "href": "https://api-m.sandbox.paypal.com/v1/customer/disputes/PP-D-12345/provide-evidence",
        "rel": "provide_evidence",
        "method": "POST"
      },
      {
        "href": "https://api-m.sandbox.paypal.com/v1/customer/disputes/PP-D-12345/accept-claim",
        "rel": "accept_claim",
        "method": "POST"
      }
    ]
  }
}
```

---

## 2. PayPal API v1 Evidence Submission Schema

### Endpoint
`POST /v1/customer/disputes/{dispute_id}/provide-evidence`

### Dual-Mode Payload Specification (Per OQ-004 Resolution)

#### Mode A: JSON-Only Payload (Tracking & Carrier Only)
```json
{
  "evidences": [
    {
      "evidence_type": "PROOF_OF_FULFILLMENT",
      "evidence_info": {
        "tracking_info": [
          {
            "carrier_name": "USPS",
            "tracking_number": "9400100000000000000000"
          }
        ]
      },
      "notes": "Order fulfilled via USPS. Delivered to customer address."
    }
  ]
}
```

#### Mode B: Multipart/Form-Data Payload (Documents & Files)
- Header: `Content-Type: multipart/form-data; boundary=BOUNDARY`
- Part 1 (`name="input"`): Application JSON with evidence metadata.
- Part 2 (`name="file1"`): Binary file (image/png, image/jpeg, or application/pdf).
- Constraints: Max 10 MB per file, max 50 MB total payload.

---

## 3. AI Reasoning Structured Output (`DisputeDecisionOutput`)

```json
{
  "recommended_action": "CONTEST",
  "win_probability": 0.88,
  "net_expected_recovery": 112.50,
  "confidence_score": 0.95,
  "seller_protection_eligible": true,
  "justification": "Tracking shows package DELIVERED to buyer postal code prior to dispute initiation.",
  "evidence_types_required": ["PROOF_OF_FULFILLMENT"],
  "customer_text_contains_injection": false,
  "requires_human_approval": true
}
```
