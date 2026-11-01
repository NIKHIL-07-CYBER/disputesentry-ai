# S02 tests: Webhook Ingestion & Cryptographic Verification Core

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T02-01` | Valid PayPal webhook signature (`DSP001`) | Headers from `catalog/fixtures/DSP001/good.json`, matching raw body bytes, RSA-SHA256 signature | HTTP 200 OK, `{"status": "success", "action": "QUEUED_FOR_EVALUATION"}` |
| `T02-02` | Tampered webhook body rejection (`DSP002`) | Input from `catalog/fixtures/DSP002/bad.json` with altered dispute amount | HTTP 401 Unauthorized, `{"error": "INVALID_SIGNATURE"}` |
| `T02-03` | Duplicate transmission deduplication (`DSP003`) | Send duplicate `PAYPAL-TRANSMISSION-ID: 7a82c3f0-...` twice | Second call returns HTTP 200 OK immediately; duplicate logged without re-processing |
| `T02-04` | SSRF certificate URL whitelist (`DSP004`) | `PAYPAL-CERT-URL: https://attacker.com/fake.pem` | HTTP 400 Bad Request, `{"error": "INVALID_CERT_URL"}` |

## Positive cases
- Valid RSA-SHA256 signed webhook returns 200 OK.
- Valid cert from `https://api.sandbox.paypal.com/v1/notifications/certs/...` is downloaded and cached in memory.

## Negative cases
- Invalid signature bytes return 401.
- Expired X.509 certificate returns 401.
- HTTP (non-SSL) cert URL returns 400.
- Certificate URL from untrusted domain (`http://evil.com`) returns 400 without initiating network fetch.

## Boundary cases
- Transmission time skewed by 4 minutes 59 seconds accepted; skewed by 5 minutes 1 second rejected.

## Fixtures and golden files used
- `catalog/fixtures/DSP001/` (`good.json`, `bad.json`, `expected.yaml`)
- `catalog/fixtures/DSP002/` (`good.json`, `bad.json`, `expected.yaml`)
- `catalog/fixtures/DSP003/` (`good.json`, `bad.json`, `expected.yaml`)
- `catalog/fixtures/DSP004/` (`good.json`, `bad.json`, `expected.yaml`)

## Commands to run (exact)
```bash
pytest tests/unit/test_webhook_verifier.py tests/integration/test_webhook_api.py -v
```

## Coverage target
- 95%+ coverage across `app/clients/webhook_verifier.py` and `app/api/webhooks.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Parsing JSON request before verifying signature (breaks raw byte digest calculation).
- Regex matching cert URL with substring match instead of strict hostname anchor (SSRF vulnerability).
