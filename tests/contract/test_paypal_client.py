"""Contract tests for PayPal Disputes REST API v1 async client."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.clients.paypal_client import (
    EvidenceValidationError,
    PayPalAPIError,
    PayPalAuthError,
    PayPalDisputesClient,
)

BASE_URL = "https://api-m.sandbox.paypal.com"


@pytest.fixture
def paypal_client() -> PayPalDisputesClient:
    """Fixture providing initialized PayPalDisputesClient."""
    return PayPalDisputesClient(
        client_id="mock_client_id",
        client_secret="mock_client_secret",
        base_url=BASE_URL,
    )


@pytest.mark.asyncio
@respx.mock
async def test_t04_01_oauth2_token_acquisition_and_cache(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T04-01: Acquire OAuth2 token, cache until expiry, and reuse without extra network call."""
    token_route = respx.post(f"{BASE_URL}/v1/oauth2/token").respond(
        status_code=200,
        json={
            "access_token": "access_token_123",
            "token_type": "Bearer",
            "expires_in": 3600,
        },
    )

    token1 = await paypal_client.get_access_token()
    assert token1 == "access_token_123"
    assert token_route.call_count == 1

    # Second call should use cache
    token2 = await paypal_client.get_access_token()
    assert token2 == "access_token_123"
    assert token_route.call_count == 1

    await paypal_client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_t04_01_token_401_retry_with_refresh(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T04-01: Client catches 401, refreshes cached token, and retries request automatically."""
    token_call_count = 0

    def token_side_effect(request: respx.Request) -> Response:
        nonlocal token_call_count
        token_call_count += 1
        return Response(
            200,
            json={
                "access_token": f"token_attempt_{token_call_count}",
                "token_type": "Bearer",
                "expires_in": 3600,
            },
        )

    respx.post(f"{BASE_URL}/v1/oauth2/token").mock(side_effect=token_side_effect)

    # First dispute call returns 401; second call returns 200
    dispute_route = respx.get(f"{BASE_URL}/v1/customer/disputes/PP-D-123").mock(
        side_effect=[
            Response(401, json={"error": "invalid_token", "error_description": "Token expired"}),
            Response(200, json={"dispute_id": "PP-D-123", "status": "WAITING_FOR_SELLER_RESPONSE"}),
        ]
    )

    data = await paypal_client.get_dispute("PP-D-123")
    assert data["dispute_id"] == "PP-D-123"
    assert dispute_route.call_count == 2
    assert token_call_count == 2

    await paypal_client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_t04_04_provide_evidence_api_submission(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T04-04: Submit tracking details to provide-evidence endpoint and verify HTTP 200 (DSP014)."""
    respx.post(f"{BASE_URL}/v1/oauth2/token").respond(
        status_code=200,
        json={"access_token": "access_token_valid", "expires_in": 3600},
    )

    evidence_route = respx.post(
        f"{BASE_URL}/v1/customer/disputes/PP-D-12345/provide-evidence"
    ).respond(
        status_code=200,
        json={"status": "EVIDENCE_SUBMITTED"},
    )

    payload = {
        "evidence_type": "PROOF_OF_FULFILLMENT",
        "carrier_name": "USPS",
        "tracking_number": "9400100000000000000001",
        "notes": "Delivered to buyer on Oct 26",
    }

    result = await paypal_client.provide_evidence("PP-D-12345", payload)
    assert result.get("status") == "EVIDENCE_SUBMITTED"
    assert evidence_route.call_count == 1

    last_request = evidence_route.calls.last.request
    assert "Bearer access_token_valid" in last_request.headers["Authorization"]

    await paypal_client.aclose()


@pytest.mark.asyncio
async def test_t04_04_missing_carrier_or_tracking_rejected(
    paypal_client: PayPalDisputesClient,
) -> None:
    """T04-04: Missing carrier or tracking number raises EvidenceValidationError before dispatch."""
    bad_payload = {
        "evidence_type": "PROOF_OF_FULFILLMENT",
        "carrier_name": "",
        "tracking_number": "",
        "notes": "Trust us",
    }

    with pytest.raises(EvidenceValidationError) as exc_info:
        await paypal_client.provide_evidence("PP-D-1014", bad_payload)

    assert exc_info.value.error_code == "MISSING_CARRIER_OR_TRACKING"
    await paypal_client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_token_auth_failure_raises_paypal_auth_error(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Negative case: Non-200 response from token endpoint raises PayPalAuthError."""
    respx.post(f"{BASE_URL}/v1/oauth2/token").respond(
        status_code=401,
        json={"error": "invalid_client", "error_description": "Client authentication failed"},
    )

    with pytest.raises(PayPalAuthError):
        await paypal_client.get_access_token()

    await paypal_client.aclose()


@pytest.mark.asyncio
@respx.mock
async def test_dispute_endpoint_error_raises_paypal_api_error(
    paypal_client: PayPalDisputesClient,
) -> None:
    """Negative case: 404 or 500 response from dispute endpoint raises PayPalAPIError."""
    respx.post(f"{BASE_URL}/v1/oauth2/token").respond(
        status_code=200,
        json={"access_token": "token_ok", "expires_in": 3600},
    )
    respx.get(f"{BASE_URL}/v1/customer/disputes/PP-D-404").respond(
        status_code=404,
        json={"name": "RESOURCE_NOT_FOUND", "message": "Dispute not found"},
    )

    with pytest.raises(PayPalAPIError) as exc_info:
        await paypal_client.get_dispute("PP-D-404")

    assert "404" in str(exc_info.value)
    await paypal_client.aclose()
