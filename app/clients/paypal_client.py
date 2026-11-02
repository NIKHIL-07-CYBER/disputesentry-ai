"""PayPal Disputes REST API v1 async client with OAuth2 token caching (ADR-001, DSP014)."""

from __future__ import annotations

import logging
import time
from typing import Any

import httpx

from app.domain.exceptions import DisputeSentryError

logger = logging.getLogger(__name__)


class PayPalAPIError(DisputeSentryError):
    """Raised when an operation against PayPal REST API fails."""

    def __init__(
        self,
        message: str,
        status_code: int | None = None,
        response_body: str = "",
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.response_body = response_body


class PayPalAuthError(PayPalAPIError):
    """Raised when OAuth 2.0 token acquisition or refresh fails."""


class EvidenceValidationError(DisputeSentryError):
    """Raised when an evidence submission payload fails client-side validation."""

    def __init__(
        self,
        message: str = "Invalid evidence submission payload",
        error_code: str = "VALIDATION_FAILED",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class PayPalDisputesClient:
    """Async client for interacting with PayPal Disputes REST API v1."""

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        base_url: str = "https://api-m.sandbox.paypal.com",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = base_url.rstrip("/")
        self._http_client = http_client
        self._owns_client = http_client is None
        self._cached_token: str | None = None
        self._token_expiry: float = 0.0

    async def _get_client(self) -> httpx.AsyncClient:
        """Resolve or initialize the underlying httpx.AsyncClient instance."""
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=15.0)
            self._owns_client = True
        return self._http_client

    async def aclose(self) -> None:
        """Close the underlying HTTP client session if owned."""
        if self._owns_client and self._http_client is not None and not self._http_client.is_closed:
            await self._http_client.aclose()

    async def __aenter__(self) -> PayPalDisputesClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        await self.aclose()

    async def get_access_token(self, force_refresh: bool = False) -> str:
        """Retrieve a valid OAuth 2.0 bearer token, using cached token if not expired."""
        now = time.time()
        if (
            not force_refresh
            and self._cached_token is not None
            and now < (self._token_expiry - 30.0)
        ):
            return self._cached_token

        client = await self._get_client()
        url = f"{self.base_url}/v1/oauth2/token"
        try:
            response = await client.post(
                url,
                auth=httpx.BasicAuth(self.client_id, self.client_secret),
                headers={"Accept": "application/json", "Accept-Language": "en_US"},
                data={"grant_type": "client_credentials"},
            )
        except httpx.RequestError as exc:
            raise PayPalAuthError(f"Network error during OAuth token request: {exc}") from exc

        if response.status_code != 200:
            raise PayPalAuthError(
                f"OAuth2 token acquisition failed ({response.status_code}): {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )

        data = response.json()
        token = data.get("access_token")
        if not token:
            raise PayPalAuthError(
                "OAuth2 response missing 'access_token'",
                status_code=response.status_code,
                response_body=response.text,
            )

        expires_in = float(data.get("expires_in", 3600))
        self._cached_token = str(token)
        self._token_expiry = now + expires_in
        return self._cached_token

    async def get_dispute(self, dispute_id: str) -> dict[str, Any]:
        """Fetch dispute resource from PayPal Disputes API v1."""
        url = f"{self.base_url}/v1/customer/disputes/{dispute_id}"
        token = await self.get_access_token()
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.get(url, headers=headers)
        except httpx.RequestError as exc:
            raise PayPalAPIError(f"Network error fetching dispute {dispute_id}: {exc}") from exc

        # Automatic 401 retry with token refresh
        if response.status_code == 401:
            logger.info("Received 401 from PayPal API, refreshing access token and retrying")
            token = await self.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = await client.get(url, headers=headers)
            except httpx.RequestError as exc:
                raise PayPalAPIError(
                    f"Network error on retry fetching dispute {dispute_id}: {exc}"
                ) from exc

        if response.status_code != 200:
            raise PayPalAPIError(
                f"GET dispute {dispute_id} failed ({response.status_code}): {response.text}",
                status_code=response.status_code,
                response_body=response.text,
            )

        payload = response.json()
        if not isinstance(payload, dict):
            raise PayPalAPIError("Expected JSON object from dispute response")
        return payload

    async def provide_evidence(
        self,
        dispute_id: str,
        evidence_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Submit evidence package to PayPal Disputes API v1 (DSP014)."""
        # Pre-dispatch validation for carrier proof of fulfillment
        evidence_type = evidence_payload.get("evidence_type")
        if evidence_type == "PROOF_OF_FULFILLMENT":
            carrier = evidence_payload.get("carrier_name")
            tracking = evidence_payload.get("tracking_number")
            if (
                not carrier
                or not str(carrier).strip()
                or not tracking
                or not str(tracking).strip()
            ):
                raise EvidenceValidationError(
                    "Carrier name and tracking number are compulsory for PROOF_OF_FULFILLMENT",
                    error_code="MISSING_CARRIER_OR_TRACKING",
                )

        url = f"{self.base_url}/v1/customer/disputes/{dispute_id}/provide-evidence"
        token = await self.get_access_token()
        client = await self._get_client()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            response = await client.post(url, headers=headers, json=evidence_payload)
        except httpx.RequestError as exc:
            raise PayPalAPIError(
                f"Network error submitting evidence for dispute {dispute_id}: {exc}"
            ) from exc

        # Automatic 401 retry with token refresh
        if response.status_code == 401:
            logger.info("Received 401 on provide-evidence, refreshing access token and retrying")
            token = await self.get_access_token(force_refresh=True)
            headers["Authorization"] = f"Bearer {token}"
            try:
                response = await client.post(url, headers=headers, json=evidence_payload)
            except httpx.RequestError as exc:
                raise PayPalAPIError(
                    f"Network error on retry submitting evidence for dispute {dispute_id}: {exc}"
                ) from exc

        if response.status_code not in (200, 201, 202, 204):
            msg = (
                f"POST provide-evidence for {dispute_id} failed "
                f"({response.status_code}): {response.text}"
            )
            raise PayPalAPIError(
                msg,
                status_code=response.status_code,
                response_body=response.text,
            )

        if response.content:
            try:
                payload = response.json()
                if isinstance(payload, dict):
                    return payload
            except Exception:
                pass
        return {"status": "EVIDENCE_SUBMITTED", "status_code": response.status_code}
