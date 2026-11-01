# PayPal Disputes REST API v1 Interaction Matrix

This document maps all PayPal Disputes REST API v1 operations, required parameters, and HTTP endpoints utilized by DisputeSentry AI.

---

## 1. Endpoint Reference

| Operation | HTTP Method & Path | Required Headers / Body | Catalog Reference |
|---|---|---|---|
| **OAuth 2.0 Token** | `POST /v1/oauth2/token` | Basic Auth (`client_id:client_secret`), `grant_type=client_credentials` | Foundation / ADR-001 |
| **Get Dispute Details** | `GET /v1/customer/disputes/{dispute_id}` | Bearer Token | `DSP005`, `DSP010` |
| **Provide Evidence** | `POST /v1/customer/disputes/{dispute_id}/provide-evidence` | Bearer Token, Multipart or JSON payload with evidence type and tracking | `DSP014`, `DSP016`, `DSP017` |
| **Accept Claim** | `POST /v1/customer/disputes/{dispute_id}/accept-claim` | Bearer Token, `{"note": "string", "accept_claim_reason": "DID_NOT_SHIP_ITEM"}` | `DSP015` |
| **Make Offer (Inquiry)** | `POST /v1/customer/disputes/{dispute_id}/make-offer` | Bearer Token, `{"offer_amount": {"currency": "USD", "value": "20.00"}, "note": "string"}` | `DSP012` |
| **Send Message** | `POST /v1/customer/disputes/{dispute_id}/send-message` | Bearer Token, `{"message": "string"}` | `DSP012` |

---

## 2. Sandbox Verification Endpoints

For automated testing in the PayPal Sandbox:
- Dispute simulation endpoints: `POST /v1/customer/disputes/{id}/adjudicate` or sandbox test event generation.
- Mock contract tests (`respx`) replay exact recorded JSON structures conforming to this specification.
