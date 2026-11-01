# Security Architecture and Threat Model

This document outlines the security controls, data protection policies, and threat mitigations implemented in DisputeSentry AI.

---

## 1. STRIDE Threat Analysis and Mitigations

| Threat Category | Specific Attack Vector | Potential Impact | Implemented Mitigation |
|---|---|---|---|
| **Spoofing** | Attacker sends forged HTTP POST requests to `/webhooks/paypal` simulating fake dispute events. | Unauthorized dispute state corruption or fraudulent claim concessions. | Strict cryptographic verification of `PAYPAL-TRANSMISSION-SIG` using PayPal's X.509 certificate. Validates cert host ends in `paypal.com`. Rejects forged signatures with HTTP 400 (`DSP001`, `DSP002`, `DSP004`). |
| **Tampering** | Man-in-the-middle or untrusted proxy alters webhook body (e.g. modifying dispute amount). | Inaccurate financial evaluation or flawed representment. | SHA-256 digest comparison against signed transmission headers detects any single-byte payload tampering (`DSP002`). |
| **Repudiation** | Operator denies approving a contested claim or claims automated engine acted without authorization. | Inability to audit unauthorized fund transfers or concessions. | Tamper-evident, append-only SQLite `audit_log` records actor ID, timestamps, before/after states, and SHA-256 payload hashes (`DSP022`). |
| **Information Disclosure** | Cardholder data (PAN, CVV) or customer PII leaks into logs, databases, or LLM prompts. | PCI DSS non-compliance, severe regulatory penalties, identity theft. | Automatic regex-based Luhn sanitizer detects and masks 13-19 digit card numbers to `[REDACTED_PAN]` before persistence or model invocation (`DSP019`). |
| **Denial of Service** | Redelivered webhook floods or oversized file uploads overwhelm server memory. | Application outage during critical dispute deadline windows. | Deduplication filter discards duplicate `transmission_id` records (`DSP003`). Hard file size ceilings (10 MB/file, 50 MB total) halt oversized uploads locally (`DSP016`). |
| **Elevation of Privilege / Injection** | Adversarial customer dispute text injects prompt override commands to force concession. | LLM agent is coerced into conceding high-value disputes or bypassing approval gates. | Untrusted buyer text is isolated inside `<untrusted_buyer_claim>` XML blocks with system prompts forbidding instruction override (`DSP020`). Critical actions require human approval (`DSP013`). |

---

## 2. Cardholder Data Environment (PCI DSS Governance)

DisputeSentry AI operates under a **Zero-PAN Storage Policy**:
1. **Scrubbing Pipeline**:
   - Inbound text from webhook payloads, dispute descriptions, and merchant records is filtered through `app.domain.sanitizer.sanitize_text()` before being stored in the database or passed to AI prompts.
2. **Detection Algorithm**:
   - Matches candidate digit sequences (13 to 19 digits with optional spaces or dashes).
   - Validates candidate numbers against the Luhn checksum (mod 10).
   - Validated card numbers are permanently overwritten with `[REDACTED_PAN]`.
3. **Sensitive Authentication Data (SAD)**:
   - 3-digit or 4-digit CVV/CVC codes adjacent to card numbers or expiration dates are stripped.

---

## 3. Secrets Management and Key Handling

1. **Zero Hardcoded Secrets**:
   - No credentials, tokens, or private keys are stored in source code or repositories.
   - Credentials (`PAYPAL_CLIENT_ID`, `PAYPAL_CLIENT_SECRET`, `PAYPAL_WEBHOOK_ID`, `GEMINI_API_KEY`) are loaded strictly from environment variables or a non-committed local `.env` file via `pydantic-settings`.
2. **OAuth Token Security**:
   - Temporary PayPal bearer tokens are cached strictly in ephemeral memory and never persisted to disk or written to application logs.
3. **Certificate Validation & SSRF Prevention**:
   - Webhook certificate downloads strictly enforce HTTPS and validate that the certificate URL host matches `^https://api(-m)?\.(sandbox\.)?paypal\.com/`. Any host outside this pattern is rejected to prevent Server-Side Request Forgery (`DSP004`).

---

## 4. Dependency Supply Chain Governance

1. **Version Pinning**:
   - All third-party dependencies are pinned with exact version numbers in `requirements.txt`.
2. **Minimal Dependency Surface**:
   - The production runtime relies on a minimal footprint (`fastapi`, `uvicorn`, `pydantic`, `httpx`, `cryptography`, `aiosqlite`, `jinja2`, `google-genai`).
3. **Automated Vulnerability Auditing**:
   - CI pipelines execute `pip-audit` or `safety` checks on every build to detect known CVEs in upstream libraries.
