"""PayPal webhook signature verification client with SSRF mitigation and cert caching."""

from __future__ import annotations

import base64
import re
import time
import urllib.parse
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime

import httpx
from cryptography import x509
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa


class SSRFSecurityError(Exception):
    """Raised when an incoming certificate URL fails PayPal domain whitelist validation."""


class SignatureVerificationError(Exception):
    """Raised when webhook cryptographic signature fails verification or cert is invalid."""


@dataclass(frozen=True)
class WebhookVerificationResult:
    """Outcome of a webhook cryptographic signature verification attempt."""

    is_valid: bool
    error_reason: str | None = None


class PayPalWebhookVerifier:
    """Verifies incoming PayPal webhook signatures using RSA-SHA256 and X.509 certificates."""

    _TRUSTED_URL_PATTERN: re.Pattern[str] = re.compile(
        r"^https://api(-m)?\.(sandbox\.)?paypal\.com/",
        re.IGNORECASE,
    )

    def __init__(
        self,
        cert_cache_ttl_seconds: int = 3600,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialize verifier with in-memory certificate cache and optional HTTP client.

        Args:
            cert_cache_ttl_seconds: Time-to-live for cached certificates in seconds (default 1h).
            http_client: Optional async httpx client for certificate downloads.
        """
        self.cert_cache_ttl_seconds = cert_cache_ttl_seconds
        self._http_client = http_client
        self._cert_cache: dict[str, tuple[x509.Certificate, float]] = {}

    @classmethod
    def is_trusted_cert_url(cls, cert_url: str) -> bool:
        """Validate that cert_url strictly targets an authorized PayPal domain.

        Args:
            cert_url: Full HTTPS URL to the PayPal X.509 certificate.

        Returns:
            bool: True if URL matches the approved PayPal certificate host whitelist.
        """
        if not cert_url or not isinstance(cert_url, str):
            return False
        if not cls._TRUSTED_URL_PATTERN.match(cert_url):
            return False
        parsed = urllib.parse.urlparse(cert_url)
        if parsed.scheme.lower() != "https":
            return False
        hostname = (parsed.hostname or "").lower()
        valid_hosts = {
            "api.paypal.com",
            "api-m.paypal.com",
            "api.sandbox.paypal.com",
            "api-m.sandbox.paypal.com",
        }
        return hostname in valid_hosts

    async def fetch_and_validate_cert(self, cert_url: str) -> x509.Certificate:
        """Fetch X.509 cert over HTTPS with domain whitelist and in-memory TTL caching.

        Args:
            cert_url: URL pointing to PayPal PEM certificate.

        Returns:
            x509.Certificate: Parsed and validated X.509 certificate.

        Raises:
            SSRFSecurityError: If cert_url fails domain whitelist validation.
            SignatureVerificationError: If fetch fails, PEM is invalid, or cert is expired.
        """
        if not self.is_trusted_cert_url(cert_url):
            raise SSRFSecurityError(
                f"Untrusted or invalid certificate URL host: {cert_url}"
            )

        now_monotonic = time.monotonic()
        if cert_url in self._cert_cache:
            cert, cached_at = self._cert_cache[cert_url]
            if now_monotonic - cached_at < self.cert_cache_ttl_seconds:
                return cert

        try:
            if self._http_client is not None:
                response = await self._http_client.get(cert_url)
            else:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(cert_url)
        except Exception as exc:
            raise SignatureVerificationError(
                f"Failed to retrieve certificate from {cert_url}: {exc}"
            ) from exc

        if response.status_code != 200:
            raise SignatureVerificationError(
                f"Failed to fetch certificate from {cert_url}: HTTP {response.status_code}"
            )

        try:
            cert = x509.load_pem_x509_certificate(response.content)
        except Exception as exc:
            raise SignatureVerificationError(
                f"Failed to parse X.509 PEM certificate: {exc}"
            ) from exc

        now_utc = datetime.now(UTC)
        if now_utc < cert.not_valid_before_utc or now_utc > cert.not_valid_after_utc:
            raise SignatureVerificationError(
                f"Certificate is expired or not yet valid "
                f"(valid range: {cert.not_valid_before_utc} to {cert.not_valid_after_utc})"
            )

        self._cert_cache[cert_url] = (cert, now_monotonic)
        return cert

    def store_cached_cert(self, cert_url: str, cert: x509.Certificate) -> None:
        """Manually seed the certificate cache for testing or offline preloading."""
        self._cert_cache[cert_url] = (cert, time.monotonic())

    @staticmethod
    def validate_transmission_time(
        transmission_time: str,
        reference_time: datetime | None = None,
        max_drift_seconds: int = 300,
    ) -> bool:
        """Check if PAYPAL-TRANSMISSION-TIME is within allowable clock drift tolerance.

        Args:
            transmission_time: ISO-8601 formatted timestamp string.
            reference_time: Optional reference UTC timestamp (defaults to current UTC time).
            max_drift_seconds: Maximum allowed clock drift in seconds (default 300 / 5 min).

        Returns:
            bool: True if timestamp is valid and within allowable skew window.
        """
        try:
            cleaned = transmission_time.replace("Z", "+00:00")
            parsed_time = datetime.fromisoformat(cleaned)
            if parsed_time.tzinfo is None:
                parsed_time = parsed_time.replace(tzinfo=UTC)
        except Exception:
            return False

        ref = reference_time or datetime.now(UTC)
        drift = abs((ref - parsed_time).total_seconds())
        return drift <= max_drift_seconds

    def verify_signature(
        self,
        raw_body: bytes,
        transmission_id: str,
        transmission_time: str,
        cert_url: str,
        auth_algo: str,
        transmission_sig: str,
        webhook_id: str,
        cert: x509.Certificate | None = None,
    ) -> bool:
        """Verify the RSA-SHA256 signature against PayPal X.509 public key.

        Payload format:
            CRC32(raw_body) + "|" + transmission_id + "|" + transmission_time + "|" + webhook_id

        Args:
            raw_body: Unmodified raw request body bytes.
            transmission_id: Value of PAYPAL-TRANSMISSION-ID header.
            transmission_time: Value of PAYPAL-TRANSMISSION-TIME header.
            cert_url: Value of PAYPAL-CERT-URL header.
            auth_algo: Value of PAYPAL-AUTH-ALGO header (e.g. SHA256withRSA).
            transmission_sig: Base64-encoded signature from PAYPAL-TRANSMISSION-SIG.
            webhook_id: Configured PayPal webhook ID.
            cert: Optional pre-validated X.509 certificate. If None, retrieved from cache.

        Returns:
            bool: True if signature is cryptographically valid, False otherwise.
        """
        target_cert = cert
        if target_cert is None:
            if cert_url in self._cert_cache:
                target_cert, _ = self._cert_cache[cert_url]
            else:
                return False

        if not auth_algo or not auth_algo.upper().startswith("SHA256WITHRSA"):
            return False

        if not transmission_sig:
            return False

        try:
            signature_bytes = base64.b64decode(transmission_sig)
        except Exception:
            return False

        crc32_val = zlib.crc32(raw_body) & 0xFFFFFFFF
        payload_str = f"{crc32_val}|{transmission_id}|{transmission_time}|{webhook_id}"
        payload_bytes = payload_str.encode("utf-8")

        public_key = target_cert.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            return False

        try:
            public_key.verify(
                signature_bytes,
                payload_bytes,
                padding.PKCS1v15(),
                hashes.SHA256(),
            )
            return True
        except InvalidSignature:
            return False
        except Exception:
            return False
