"""PayPal webhook ingestion and cryptographic verification endpoint."""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

from app.clients.webhook_verifier import (
    PayPalWebhookVerifier,
    SignatureVerificationError,
    SSRFSecurityError,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["webhooks"])


@router.post("/webhooks/paypal")
async def ingest_paypal_webhook(request: Request) -> JSONResponse:
    """Ingest, verify, deduplicate, and acknowledge inbound PayPal webhook events.

    Executes:
    1. Raw body capture before any mutation or deserialization.
    2. Transmission header extraction and validation.
    3. In-memory deduplication check for PAYPAL-TRANSMISSION-ID.
    4. SSRF domain check and X.509 certificate fetching/caching.
    5. RSA-SHA256 signature verification over CRC32(raw_body)|tx_id|tx_time|webhook_id.
    """
    # 1. Capture raw bytes first to preserve byte-exact content for signature verification
    raw_body = await request.body()

    # 2. Extract transmission headers
    auth_algo = request.headers.get("paypal-auth-algo")
    cert_url = request.headers.get("paypal-cert-url")
    transmission_id = request.headers.get("paypal-transmission-id")
    transmission_sig = request.headers.get("paypal-transmission-sig")
    transmission_time = request.headers.get("paypal-transmission-time")

    if not all([auth_algo, cert_url, transmission_id, transmission_sig, transmission_time]):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "MISSING_HEADERS",
                "message": (
                    "Missing required PayPal webhook headers: PAYPAL-AUTH-ALGO, "
                    "PAYPAL-CERT-URL, PAYPAL-TRANSMISSION-ID, PAYPAL-TRANSMISSION-SIG, "
                    "PAYPAL-TRANSMISSION-TIME"
                ),
            },
        )

    # TypeScript / mypy type narrowing guarantees transmission_id is str here
    assert transmission_id is not None
    assert cert_url is not None
    assert auth_algo is not None
    assert transmission_sig is not None
    assert transmission_time is not None

    # 3. Deduplication check
    raw_processed = getattr(request.app.state, "webhook_processed_transmissions", None)
    if isinstance(raw_processed, set):
        processed_transmissions: set[str] = raw_processed
    else:
        processed_transmissions = set()
        request.app.state.webhook_processed_transmissions = processed_transmissions

    if transmission_id in processed_transmissions:
        logger.info(
            "Duplicate webhook transmission ignored: transmission_id=%s",
            transmission_id,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "status": "duplicate_ignored",
                "transmission_id": transmission_id,
                "duplicate": True,
            },
        )

    # 4. Resolve verifier client
    raw_verifier = getattr(request.app.state, "webhook_verifier", None)
    if isinstance(raw_verifier, PayPalWebhookVerifier):
        verifier = raw_verifier
    else:
        verifier = PayPalWebhookVerifier()
        request.app.state.webhook_verifier = verifier

    # 5. Fetch and validate certificate (SSRF defense + X.509 validity)
    try:
        cert = await verifier.fetch_and_validate_cert(cert_url)
    except SSRFSecurityError as exc:
        logger.warning(
            "SSRF certificate URL rejected: url=%s reason=%s", cert_url, exc
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": "INVALID_CERT_URL",
                "error_code": "UNTRUSTED_CERT_URL",
                "message": str(exc),
            },
        )
    except SignatureVerificationError as exc:
        logger.warning(
            "Certificate verification failed: url=%s reason=%s", cert_url, exc
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "INVALID_SIGNATURE",
                "error_code": "INVALID_SIGNATURE",
                "message": str(exc),
            },
        )

    # 6. Verify RSA-SHA256 signature
    config: Any = getattr(request.app.state, "config", None)
    configured_wh_id = str(config.paypal_webhook_id) if config else "WH-SANDBOX-12345"

    is_valid = verifier.verify_signature(
        raw_body=raw_body,
        transmission_id=transmission_id,
        transmission_time=transmission_time,
        cert_url=cert_url,
        auth_algo=auth_algo,
        transmission_sig=transmission_sig,
        webhook_id=configured_wh_id,
        cert=cert,
    )

    if not is_valid:
        logger.warning(
            "Webhook signature verification failed: transmission_id=%s",
            transmission_id,
        )
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "INVALID_SIGNATURE",
                "error_code": "INVALID_SIGNATURE",
                "message": "Cryptographic signature verification failed",
            },
        )

    # 7. Signature authentic - record transmission for deduplication
    processed_transmissions.add(transmission_id)

    # Extract event metadata without logging sensitive payload fields
    event_id: str | None = None
    dispute_id: str | None = None
    try:
        payload_dict = json.loads(raw_body.decode("utf-8"))
        if isinstance(payload_dict, dict):
            raw_event_id = payload_dict.get("id")
            event_id = str(raw_event_id) if raw_event_id is not None else None
            resource = payload_dict.get("resource")
            if isinstance(resource, dict):
                raw_dispute_id = resource.get("dispute_id")
                dispute_id = str(raw_dispute_id) if raw_dispute_id is not None else None
    except Exception:
        pass

    logger.info(
        "Authentic PayPal webhook verified: transmission_id=%s event_id=%s dispute_id=%s",
        transmission_id,
        event_id,
        dispute_id,
    )

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": "success",
            "action": "QUEUED_FOR_EVALUATION",
            "transmission_id": transmission_id,
            "event_id": event_id,
            "dispute_id": dispute_id,
            "duplicate": False,
        },
    )
