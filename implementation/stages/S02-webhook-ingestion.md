# S02 Webhook Ingestion and Cryptographic Verification Core

## 1 Goal and outcome
Implement the PayPal webhook verification client (`app/clients/webhook_verifier.py`) and FastAPI webhook ingestion route (`app/api/webhooks.py`). Authenticate incoming webhooks using RSA-SHA256, prevent SSRF via cert URL whitelisting, deduplicate transmission IDs, and dispatch valid dispute events.

## 2 Entry conditions
- Stage S01 complete (`tests/test_catalog_fixtures.py` operational).
- `cryptography` library installed and importable.

## 3 Read first
1. `catalog/DSP001.yaml`, `catalog/DSP002.yaml`, `catalog/DSP003.yaml`, `catalog/DSP004.yaml`
2. `docs/SPEC.md` §4.2.1
3. `implementation/assets/flows/WEBHOOK_INGESTION_FLOW.md`
4. `implementation/assets/architecture/PACKAGE_BOUNDARIES.md`
5. `implementation/tests/S02-tests.md`

## 4 Files to create or modify
- `app/clients/__init__.py`
- `app/clients/webhook_verifier.py`
- `app/api/__init__.py`
- `app/api/webhooks.py`
- `app/main.py` (mount webhook router)
- `tests/unit/test_webhook_verifier.py`
- `tests/integration/test_webhook_api.py`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- Do not bypass signature verification in production code.
- Never write cardholder data to logs.

## 6 Interfaces and signatures
```python
from cryptography.x509 import Certificate

class WebhookVerificationResult:
    is_valid: bool
    error_reason: str | None

class PayPalWebhookVerifier:
    def __init__(self, cert_cache_ttl_seconds: int = 3600): ...
    async def fetch_and_validate_cert(self, cert_url: str) -> Certificate: ...
    def verify_signature(
        self,
        raw_body: bytes,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
        webhook_id: str,
    ) -> bool: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP001` | `catalog/fixtures/DSP001/` | Request signature is verified as authentic; returns HTTP 200 OK | Extract transmission headers, validate cert URL, verify RSA-SHA256 against public key | `applies_when`, `expected.outcome` |
| `DSP002` | `catalog/fixtures/DSP002/` | Tampered body rejected; returns HTTP 401 Unauthorized | Recompute digest over altered bytes; detect mismatch with transmission signature | `applies_when`, `correct_alternative` |
| `DSP003` | `catalog/fixtures/DSP003/` | Duplicate transmission ID returns HTTP 200 without duplicate processing | Check transmission ID in processed cache; return 200 OK immediately if exists | `applies_when`, `expected.outcome` |
| `DSP004` | `catalog/fixtures/DSP004/` | Certificate URL outside `*.paypal.com` rejected with HTTP 400 Bad Request | Strict regex validation on cert URL hostname matching trusted PayPal domain before fetch | `applies_when`, `correct_alternative` |

## 8 Step-by-step instructions
1. Write tests in `tests/unit/test_webhook_verifier.py` and `tests/integration/test_webhook_api.py` per `S02-tests.md`. Verify they fail.
2. Implement `app/clients/webhook_verifier.py`:
   - Enforce domain whitelist regex `^https://api(\.sandbox)?\.paypal\.com/` on `PAYPAL-CERT-URL`.
   - Fetch certificate asynchronously via `httpx` and cache in-memory using LRU dictionary.
   - Construct PayPal signature payload: `CRC32(raw_body) + "|" + transmission_id + "|" + transmission_time + "|" + webhook_id`.
   - Verify RSA-SHA256 signature against X.509 public key using `cryptography`.
3. Implement `POST /webhooks/paypal` endpoint in `app/api/webhooks.py`:
   - Capture `request.body()` raw bytes before any parsing.
   - Extract required headers (`PAYPAL-AUTH-ALGO`, `PAYPAL-TRANSMISSION-ID`, etc.).
   - Check deduplication store for `PAYPAL-TRANSMISSION-ID`.
   - Invoke verifier; return HTTP 400 on SSRF failure, HTTP 401 on signature mismatch, HTTP 200 on success.
4. Wire router into `app/main.py`.
5. Run tests until 100% green.

## 9 Edge cases
- Subdomain spoofing attempts (e.g., `https://api.sandbox.paypal.com.evil.com/cert.pem`).
- Clock drift up to 5 minutes permitted in `PAYPAL-TRANSMISSION-TIME`.

## 10 Out of scope
- Database persistence of disputes (handled in S03).
- PayPal API outbound calls (handled in S04).

## 11 Tests
Follow instructions in `implementation/tests/S02-tests.md`. Wire `DSP001` - `DSP004` into `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- `pytest tests/unit/test_webhook_verifier.py tests/integration/test_webhook_api.py` passes 100%.
- Catalog fixtures `DSP001`, `DSP002`, `DSP003`, `DSP004` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(webhooks): implement rsa-sha256 signature verification, ssrf cert whitelist, and deduplication (DSP001-DSP004)`

## 14 Failure and rollback handling
If signature checks fail in tests, verify that `raw_body` bytes are not being mutated by JSON parser or middleware.

## 15 Handoff notes for the next stage
Provides verified webhook ingestion pipeline for S03 (Domain Models and Data Layer).
