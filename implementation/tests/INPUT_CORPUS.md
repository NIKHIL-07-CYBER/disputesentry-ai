# Curated Input Corpus for Edge-Case Testing

This document catalogs test cases designed to stress parser resilience and security boundaries.

---

## 1. Corpus Items

1. **Large Unicode Payload:** Inbound webhook message containing 50,000 multi-byte emojis and zero-width joiners. Verifies database and tokenizer memory limits.
2. **Missing Webhook Headers:** Request omitting `PAYPAL-TRANSMISSION-SIG` or `PAYPAL-CERT-URL`. Verifies 400 Bad Request return without stack trace leak.
3. **HTTP Cert URL (MITM Attempt):** `PAYPAL-CERT-URL` using `http://` instead of `https://`. Must be rejected by SSRF guard.
4. **Boundary Timestamp (Due Date in 2 hours):** Dispute with `seller_response_due_date` exactly 120 minutes from current UTC. Must trigger fail-safe fallback trigger.
5. **Exact 50 MB Multipart Payload:** Request containing multiple attachments totaling 52,428,800 bytes. Must succeed; 52,428,801 bytes must be rejected with 413.
