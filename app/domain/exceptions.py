"""Domain exceptions for DisputeSentry AI."""

from __future__ import annotations


class DisputeSentryError(Exception):
    """Base exception for all domain and operational failures."""


class OrderNotFoundError(DisputeSentryError):
    """Raised when a merchant order matching transaction_id is not found."""


class AuditIntegrityError(DisputeSentryError):
    """Raised when audit trail chain hash verification fails or tampering is detected."""


class AuditImmutableError(DisputeSentryError):
    """Raised when attempting to modify or delete audit log entries."""
