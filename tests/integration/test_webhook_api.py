"""Integration tests for PayPal webhook ingestion API endpoint."""

from __future__ import annotations

import base64
import json
import zlib
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import respx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID
from httpx import ASGITransport, AsyncClient

from app.config import get_config
from app.main import create_app

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "catalog" / "fixtures"


@pytest.fixture
def rsa_keypair() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Generate RSA private key and self-signed certificate."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COMMON_NAME, "api.sandbox.paypal.com"),
    ])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(private_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(private_key, hashes.SHA256())
    )
    return private_key, cert


def sign_payload(
    private_key: rsa.RSAPrivateKey,
    raw_body: bytes,
    transmission_id: str,
    transmission_time: str,
    webhook_id: str,
) -> str:
    """Helper to compute PayPal RSA-SHA256 signature over CRC32 payload."""
    crc32_val = zlib.crc32(raw_body) & 0xFFFFFFFF
    payload_str = f"{crc32_val}|{transmission_id}|{transmission_time}|{webhook_id}"
    signature = private_key.sign(
        payload_str.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("utf-8")


@pytest.mark.asyncio
@respx.mock
async def test_t02_01_valid_paypal_webhook_signature(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """T02-01: Valid PayPal webhook signature returns 200 OK and queues event (DSP001)."""
    private_key, cert = rsa_keypair
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-001.pem"
    respx.get(cert_url).respond(
        status_code=200, content=cert.public_bytes(serialization.Encoding.PEM)
    )

    dsp001_good_path = FIXTURES_DIR / "DSP001" / "good.json"
    data = json.loads(dsp001_good_path.read_text(encoding="utf-8"))

    raw_body = json.dumps(data["body"]).encode("utf-8")
    tx_id = data["headers"]["PAYPAL-TRANSMISSION-ID"]
    tx_time = data["headers"]["PAYPAL-TRANSMISSION-TIME"]
    webhook_id = "WH-SANDBOX-12345"

    sig = sign_payload(private_key, raw_body, tx_id, tx_time, webhook_id)

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": cert_url,
        "PAYPAL-TRANSMISSION-ID": tx_id,
        "PAYPAL-TRANSMISSION-SIG": sig,
        "PAYPAL-TRANSMISSION-TIME": tx_time,
        "Content-Type": "application/json",
    }

    config = get_config(paypal_webhook_id=webhook_id)
    app = create_app(config=config)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/paypal", content=raw_body, headers=headers)

    assert response.status_code == 200
    res_data = response.json()
    assert res_data["status"] == "success"
    assert res_data["action"] == "QUEUED_FOR_EVALUATION"
    assert res_data["dispute_id"] == "PP-D-1001"


@pytest.mark.asyncio
@respx.mock
async def test_t02_02_tampered_webhook_body_rejected(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """T02-02: Tampered webhook body rejected with HTTP 401 Unauthorized (DSP002)."""
    private_key, cert = rsa_keypair
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-002.pem"
    respx.get(cert_url).respond(
        status_code=200, content=cert.public_bytes(serialization.Encoding.PEM)
    )

    dsp002_bad_path = FIXTURES_DIR / "DSP002" / "bad.json"
    data = json.loads(dsp002_bad_path.read_text(encoding="utf-8"))

    # Original body is for 50.00, but data["body"] has 9999.00
    original_body = json.dumps({"dispute_amount": {"value": "50.00"}}).encode("utf-8")
    tampered_body = json.dumps(data["body"]).encode("utf-8")

    tx_id = data["headers"]["PAYPAL-TRANSMISSION-ID"]
    tx_time = data["headers"]["PAYPAL-TRANSMISSION-TIME"]
    webhook_id = "WH-SANDBOX-12345"

    # Signature signed over ORIGINAL body, but sending TAMPERED body
    sig = sign_payload(private_key, original_body, tx_id, tx_time, webhook_id)

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": cert_url,
        "PAYPAL-TRANSMISSION-ID": tx_id,
        "PAYPAL-TRANSMISSION-SIG": sig,
        "PAYPAL-TRANSMISSION-TIME": tx_time,
        "Content-Type": "application/json",
    }

    config = get_config(paypal_webhook_id=webhook_id)
    app = create_app(config=config)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/paypal", content=tampered_body, headers=headers)

    assert response.status_code == 401
    res_data = response.json()
    assert res_data["error"] == "INVALID_SIGNATURE"


@pytest.mark.asyncio
@respx.mock
async def test_t02_03_duplicate_transmission_deduplication(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """T02-03: Duplicate transmission returns HTTP 200 without duplicate processing (DSP003)."""
    private_key, cert = rsa_keypair
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-003.pem"
    respx.get(cert_url).respond(
        status_code=200, content=cert.public_bytes(serialization.Encoding.PEM)
    )

    body_obj = {
        "id": "WH-EV-003",
        "event_type": "CUSTOMER.DISPUTE.CREATED",
        "resource": {"dispute_id": "PP-D-1003"},
    }
    raw_body = json.dumps(body_obj).encode("utf-8")
    tx_id = "tx-unique-12345"
    tx_time = "2026-11-01T12:00:00Z"
    webhook_id = "WH-SANDBOX-12345"

    sig = sign_payload(private_key, raw_body, tx_id, tx_time, webhook_id)

    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": cert_url,
        "PAYPAL-TRANSMISSION-ID": tx_id,
        "PAYPAL-TRANSMISSION-SIG": sig,
        "PAYPAL-TRANSMISSION-TIME": tx_time,
        "Content-Type": "application/json",
    }

    config = get_config(paypal_webhook_id=webhook_id)
    app = create_app(config=config)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First delivery -> status success
        res1 = await client.post("/webhooks/paypal", content=raw_body, headers=headers)
        assert res1.status_code == 200
        assert res1.json()["status"] == "success"
        assert res1.json().get("duplicate") is False

        # Redelivery with identical transmission ID -> status duplicate_ignored
        res2 = await client.post("/webhooks/paypal", content=raw_body, headers=headers)
        assert res2.status_code == 200
        assert res2.json()["status"] == "duplicate_ignored"
        assert res2.json().get("duplicate") is True


@pytest.mark.asyncio
async def test_t02_04_ssrf_cert_url_whitelist_rejected() -> None:
    """T02-04: Untrusted certificate URL returns HTTP 400 Bad Request (DSP004)."""
    raw_body = b'{"event": "test"}'
    headers = {
        "PAYPAL-AUTH-ALGO": "SHA256withRSA",
        "PAYPAL-CERT-URL": "https://attacker.evil.com/fake-paypal-cert.pem",
        "PAYPAL-TRANSMISSION-ID": "tx-attacker-001",
        "PAYPAL-TRANSMISSION-SIG": "dGVzdC1zaWc=",
        "PAYPAL-TRANSMISSION-TIME": "2026-11-01T12:00:00Z",
        "Content-Type": "application/json",
    }

    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/webhooks/paypal", content=raw_body, headers=headers)

    assert response.status_code == 400
    res_data = response.json()
    assert res_data["error"] == "INVALID_CERT_URL"


@pytest.mark.asyncio
async def test_webhook_missing_required_headers_returns_400() -> None:
    """Missing required PayPal transmission headers returns HTTP 400."""
    app = create_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/webhooks/paypal",
            content=b'{"id": "test"}',
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 400
    assert response.json()["error"] == "MISSING_HEADERS"
