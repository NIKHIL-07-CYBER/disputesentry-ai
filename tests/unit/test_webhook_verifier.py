"""Unit tests for PayPal webhook verification and cryptographic client."""

from __future__ import annotations

import base64
import zlib
from datetime import UTC, datetime, timedelta

import pytest
import respx
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.x509.oid import NameOID

from app.clients.webhook_verifier import (
    PayPalWebhookVerifier,
    SignatureVerificationError,
    SSRFSecurityError,
)


@pytest.fixture
def rsa_keypair() -> tuple[rsa.RSAPrivateKey, x509.Certificate]:
    """Generate RSA private key and self-signed certificate."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, "PayPal, Inc."),
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


@pytest.fixture
def expired_cert(rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate]) -> x509.Certificate:
    """Generate an expired certificate."""
    private_key, _ = rsa_keypair
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
        .not_valid_before(now - timedelta(days=60))
        .not_valid_after(now - timedelta(days=1))
        .sign(private_key, hashes.SHA256())
    )
    return cert


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
async def test_ssrf_cert_whitelist_accepts_valid_paypal_domains() -> None:
    """Verify whitelist regex allows valid sandbox and live PayPal certificate hosts."""
    verifier = PayPalWebhookVerifier()
    valid_urls = [
        "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-123.pem",
        "https://api.paypal.com/v1/notifications/certs/CERT-456.pem",
        "https://api-m.sandbox.paypal.com/v1/notifications/certs/CERT-789.pem",
        "https://api-m.paypal.com/v1/notifications/certs/CERT-000.pem",
    ]
    for url in valid_urls:
        assert verifier.is_trusted_cert_url(url) is True


@pytest.mark.asyncio
async def test_ssrf_cert_whitelist_rejects_untrusted_and_spoofed_domains() -> None:
    """Verify whitelist rejects non-SSL, malicious subdomains, and foreign hosts."""
    verifier = PayPalWebhookVerifier()
    invalid_urls = [
        "http://api.sandbox.paypal.com/cert.pem",  # Plain HTTP
        "https://attacker.com/fake.pem",  # Foreign domain
        "https://api.sandbox.paypal.com.attacker.com/cert.pem",  # Subdomain spoofing
        "https://evil-paypal.com/cert.pem",  # Suffix trick
        "ftp://api.paypal.com/cert.pem",  # Non-HTTP scheme
        "https://192.168.1.1/cert.pem",  # IP address
    ]
    for url in invalid_urls:
        assert verifier.is_trusted_cert_url(url) is False
        with pytest.raises(SSRFSecurityError):
            await verifier.fetch_and_validate_cert(url)


@pytest.mark.asyncio
@respx.mock
async def test_cert_fetch_and_caching(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """Verify cert is fetched over HTTPS and cached in-memory."""
    _, cert = rsa_keypair
    cert_pem = cert.public_bytes(serialization.Encoding.PEM)
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1.pem"

    route = respx.get(cert_url).respond(status_code=200, content=cert_pem)

    verifier = PayPalWebhookVerifier(cert_cache_ttl_seconds=3600)
    fetched_1 = await verifier.fetch_and_validate_cert(cert_url)
    assert fetched_1.serial_number == cert.serial_number
    assert route.call_count == 1

    # Second call should hit in-memory cache without outbound network call
    fetched_2 = await verifier.fetch_and_validate_cert(cert_url)
    assert fetched_2.serial_number == cert.serial_number
    assert route.call_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_expired_cert_raises_verification_error(
    expired_cert: x509.Certificate,
) -> None:
    """Verify expired X.509 certificate is rejected."""
    cert_pem = expired_cert.public_bytes(serialization.Encoding.PEM)
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-EXPIRED.pem"

    respx.get(cert_url).respond(status_code=200, content=cert_pem)

    verifier = PayPalWebhookVerifier()
    with pytest.raises(SignatureVerificationError, match="expired"):
        await verifier.fetch_and_validate_cert(cert_url)


def test_signature_verification_success(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """Verify valid RSA-SHA256 signature passes verification."""
    private_key, cert = rsa_keypair
    raw_body = b'{"event_type": "CUSTOMER.DISPUTE.CREATED", "id": "WH-1"}'
    tx_id = "tx-12345"
    tx_time = "2026-11-01T12:00:00Z"
    wh_id = "WH-CONFIG-ID"

    sig = sign_payload(private_key, raw_body, tx_id, tx_time, wh_id)

    verifier = PayPalWebhookVerifier()
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1.pem"
    verifier.store_cached_cert(cert_url, cert)

    is_valid = verifier.verify_signature(
        raw_body=raw_body,
        transmission_id=tx_id,
        transmission_time=tx_time,
        cert_url=cert_url,
        auth_algo="SHA256withRSA",
        transmission_sig=sig,
        webhook_id=wh_id,
    )
    assert is_valid is True


def test_signature_verification_fails_on_tampered_body(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """Verify modifying body bytes invalidates signature."""
    private_key, cert = rsa_keypair
    original_body = b'{"amount": "50.00"}'
    tampered_body = b'{"amount": "9999.00"}'
    tx_id = "tx-12345"
    tx_time = "2026-11-01T12:00:00Z"
    wh_id = "WH-CONFIG-ID"

    sig = sign_payload(private_key, original_body, tx_id, tx_time, wh_id)

    verifier = PayPalWebhookVerifier()
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1.pem"
    verifier.store_cached_cert(cert_url, cert)

    is_valid = verifier.verify_signature(
        raw_body=tampered_body,
        transmission_id=tx_id,
        transmission_time=tx_time,
        cert_url=cert_url,
        auth_algo="SHA256withRSA",
        transmission_sig=sig,
        webhook_id=wh_id,
    )
    assert is_valid is False


def test_signature_verification_fails_on_corrupt_signature(
    rsa_keypair: tuple[rsa.RSAPrivateKey, x509.Certificate],
) -> None:
    """Verify invalid/corrupt base64 signature returns False."""
    _, cert = rsa_keypair
    raw_body = b'{"event": "test"}'
    tx_id = "tx-12345"
    tx_time = "2026-11-01T12:00:00Z"
    wh_id = "WH-CONFIG-ID"

    verifier = PayPalWebhookVerifier()
    cert_url = "https://api.sandbox.paypal.com/v1/notifications/certs/CERT-1.pem"
    verifier.store_cached_cert(cert_url, cert)

    # Empty or corrupt signature
    assert (
        verifier.verify_signature(
            raw_body=raw_body,
            transmission_id=tx_id,
            transmission_time=tx_time,
            cert_url=cert_url,
            auth_algo="SHA256withRSA",
            transmission_sig="",
            webhook_id=wh_id,
        )
        is False
    )
    assert (
        verifier.verify_signature(
            raw_body=raw_body,
            transmission_id=tx_id,
            transmission_time=tx_time,
            cert_url=cert_url,
            auth_algo="SHA256withRSA",
            transmission_sig="bad-base64!!",
            webhook_id=wh_id,
        )
        is False
    )


def test_transmission_time_drift_boundary() -> None:
    """Verify clock drift boundary: 4m59s accepted, 5m1s rejected."""
    verifier = PayPalWebhookVerifier()
    ref_time = datetime(2026, 11, 1, 12, 0, 0, tzinfo=UTC)

    # 4 min 59 sec drift -> should be valid
    time_4m59s = (ref_time + timedelta(minutes=4, seconds=59)).isoformat()
    assert (
        verifier.validate_transmission_time(
            time_4m59s, reference_time=ref_time, max_drift_seconds=300
        )
        is True
    )

    # 5 min 1 sec drift -> should be invalid
    time_5m01s = (ref_time + timedelta(minutes=5, seconds=1)).isoformat()
    assert (
        verifier.validate_transmission_time(
            time_5m01s, reference_time=ref_time, max_drift_seconds=300
        )
        is False
    )
