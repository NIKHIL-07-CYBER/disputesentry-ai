# Webhook Ingestion Flow

This document specifies the cryptographic verification, SSRF check, deduplication, and parsing pipeline executed for every inbound request at `POST /webhooks/paypal`.

---

## 1. Sequence Flow Diagram

```mermaid
sequenceDiagram
    autonumber
    participant PP as PayPal Webhook Engine
    participant WH as app/api/webhooks.py
    participant V as app/clients/webhook_verifier.py
    participant DB as SQLite Storage (WAL)
    participant Q as Dispute Sync Service

    PP->>WH: POST /webhooks/paypal (Headers + Raw Body)
    WH->>V: verify_inbound_request(headers, raw_body)
    
    rect rgb(240, 248, 255)
    Note over V: Step 1: SSRF Defense
    V->>V: Validate PAYPAL-CERT-URL against *.paypal.com domain
    alt Invalid domain or HTTP scheme
        V-->>WH: Raise SSRFSecurityError
        WH-->>PP: HTTP 400 Bad Request
    end
    end

    rect rgb(255, 245, 245)
    Note over V: Step 2: Deduplication Check
    V->>DB: Check PAYPAL-TRANSMISSION-ID exists
    alt Already processed
        V-->>WH: Return DUPLICATE_EVENT
        WH-->>PP: HTTP 200 OK (Idempotent acknowledge)
    end
    end

    rect rgb(245, 255, 245)
    Note over V: Step 3: Cryptographic Signature
    V->>V: Fetch & cache X.509 cert; verify RSA-SHA256 signature
    alt Signature mismatch or expired cert
        V-->>WH: Raise SignatureVerificationError
        WH-->>PP: HTTP 401 Unauthorized
    end
    end

    V-->>WH: Signature Verified OK
    WH->>DB: Record transmission_id & raw event
    WH->>Q: Dispatch event to Dispute Sync Service
    WH-->>PP: HTTP 200 OK
```

---

## 2. Invariants & Guardrails

1. **Raw Body Preservation:** The signature check MUST run against raw, unparsed request bytes before any JSON decoding or whitespace mutation.
2. **SSRF Whitelist:** `PAYPAL-CERT-URL` must strictly use HTTPS and resolve to an approved PayPal host: `^https://api(\.sandbox)?\.paypal\.com/`.
3. **Idempotency:** A duplicate `transmission_id` must return HTTP 200 OK immediately without triggering re-evaluation or duplicate audit entries.
