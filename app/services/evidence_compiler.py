"""Evidence attachment compilation, validation, and multipart packaging (S08, DSP016, DSP017)."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.domain.exceptions import DisputeSentryError

logger = logging.getLogger(__name__)


class EvidenceCompilerError(DisputeSentryError):
    """Base exception for evidence packaging and validation errors."""

    def __init__(
        self,
        message: str = "Evidence compilation failed",
        error_code: str = "VALIDATION_FAILED",
    ) -> None:
        super().__init__(message)
        self.error_code = error_code


class PayloadSizeLimitExceededError(EvidenceCompilerError):
    """Raised when an individual evidence attachment exceeds the maximum size ceiling (10MB)."""

    def __init__(
        self,
        message: str = "File exceeds 10MB limit",
        error_code: str = "PAYLOAD_TOO_LARGE",
    ) -> None:
        super().__init__(message, error_code=error_code)


class TotalPayloadSizeExceededError(EvidenceCompilerError):
    """Raised when the cumulative size of evidence attachments exceeds the maximum limit (50MB)."""

    def __init__(
        self,
        message: str = "Cumulative size exceeds 50MB limit",
        error_code: str = "PAYLOAD_TOO_LARGE",
    ) -> None:
        super().__init__(message, error_code=error_code)


class UnsupportedMimeTypeError(EvidenceCompilerError):
    """Raised when attachment MIME or magic bytes are not in the allowed whitelist."""

    def __init__(
        self,
        message: str = "Only JPG, PNG, GIF, and PDF allowed",
        error_code: str = "UNSUPPORTED_FILE_TYPE",
    ) -> None:
        super().__init__(message, error_code=error_code)


class EmptyFileError(UnsupportedMimeTypeError):
    """Raised when an attachment file is empty (0 bytes)."""

    def __init__(
        self,
        message: str = "File is empty (0 bytes)",
        error_code: str = "EMPTY_FILE",
    ) -> None:
        super().__init__(message, error_code=error_code)


class MalformedEvidencePartError(EvidenceCompilerError):
    """Raised when multipart or metadata payload structure is missing required parts."""

    def __init__(
        self,
        message: str = "Malformed evidence payload structure",
        error_code: str = "MALFORMED_EVIDENCE_PART",
    ) -> None:
        super().__init__(message, error_code=error_code)


def detect_mime_type_from_bytes(header: bytes) -> str | None:
    """Inspect magic bytes of buffer and return standard MIME type, or None if unrecognized."""
    if not header:
        return None
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if header.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if header.startswith(b"%PDF-"):
        return "application/pdf"
    if (
        header.startswith(b"GIF87a")
        or header.startswith(b"GIF89a")
        or header.startswith(b"GIF8")
    ):
        return "image/gif"
    return None


@dataclass(frozen=True)
class CompiledEvidencePayload:
    """Compiled and validated evidence payload ready for PayPal Disputes API dispatch."""

    content_type: str
    body_bytes: bytes
    total_size_bytes: int


class EvidenceCompiler:
    """Service for validating evidence document attachments and compiling multipart API payloads."""

    MAX_FILE_SIZE: int = 10 * 1024 * 1024       # 10 MB = 10,485,760 bytes (DSP016)
    MAX_TOTAL_SIZE: int = 50 * 1024 * 1024      # 50 MB = 52,428,800 bytes (DSP016)
    ALLOWED_MIMES: set[str] = {"image/jpeg", "image/png", "image/gif", "application/pdf"}  # DSP017

    @classmethod
    def detect_mime_type(cls, header: bytes) -> str | None:
        """Inspect byte header and return detected MIME type."""
        return detect_mime_type_from_bytes(header)

    @classmethod
    def inspect_file_mime(cls, path: Path) -> str:
        """Inspect file on disk, verify magic bytes, and return MIME type or raise error."""
        if not path.is_file():
            raise FileNotFoundError(f"Evidence file not found: {path}")

        size = path.stat().st_size
        if size == 0:
            raise UnsupportedMimeTypeError(f"File {path.name} is empty (0 bytes)")

        with path.open("rb") as f:
            header = f.read(32)

        mime = cls.detect_mime_type(header)
        if mime is None or mime not in cls.ALLOWED_MIMES:
            raise UnsupportedMimeTypeError("Only JPG, PNG, GIF, and PDF allowed")
        return mime

    @classmethod
    def evaluate_size_limits(cls, files: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate file metadata against PayPal 10MB per-file and 50MB total limits (DSP016)."""
        total_size = 0
        oversized: list[str] = []

        for f in files:
            name = str(f.get("name") or f.get("filename") or "unknown")
            size = int(f.get("size_bytes", 0))
            total_size += size
            if size > cls.MAX_FILE_SIZE:
                size_mb = size / (1024 * 1024)
                oversized.append(f"{name} ({size_mb:.1f} MB exceeds 10 MB limit)")

        if total_size > cls.MAX_TOTAL_SIZE and not oversized:
            total_mb = total_size / (1024 * 1024)
            oversized.append(f"Cumulative payload ({total_mb:.1f} MB exceeds 50 MB limit)")

        if oversized:
            return {
                "validation": "invalid",
                "outcome": "rejected_locally",
                "error_code": "PAYLOAD_TOO_LARGE",
                "oversized_files": oversized,
            }

        return {
            "validation": "valid",
            "total_size_bytes": total_size,
            "outcome": "upload_permitted",
        }

    @classmethod
    def evaluate_file_types(cls, files: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate file metadata dictionaries against allowed MIME type whitelist (DSP017)."""
        disallowed: list[str] = []

        for f in files:
            name = str(f.get("filename") or f.get("name") or "unknown")
            mime = str(f.get("mime_type", ""))
            if mime not in cls.ALLOWED_MIMES:
                disallowed.append(f"{name} ({mime})")

        if disallowed:
            return {
                "validation": "invalid",
                "outcome": "rejected_locally",
                "error_code": "UNSUPPORTED_FILE_TYPE",
                "disallowed_files": disallowed,
            }

        return {
            "validation": "valid",
            "outcome": "formats_accepted",
        }

    @classmethod
    def validate_and_compile(
        cls,
        evidence_type: str,
        notes: str,
        tracking_info: list[dict[str, Any]] | None = None,
        file_paths: list[Path] | None = None,
    ) -> CompiledEvidencePayload:
        """Validate input parameters and files, compiling application/json or multipart payload.

        Parameters:
            evidence_type: PayPal evidence category (e.g. PROOF_OF_DELIVERY).
            notes: Merchant explanation or context notes.
            tracking_info: Optional list of carrier tracking dictionaries.
            file_paths: Optional list of attachment file paths to validate and encode.

        Returns:
            CompiledEvidencePayload containing Content-Type, raw byte payload, and size.
        """
        if not evidence_type or not evidence_type.strip():
            raise MalformedEvidencePartError("evidence_type is required")

        # Mode A: JSON-only tracking payload (no file attachments)
        if not file_paths:
            payload_dict: dict[str, Any] = {
                "evidence_type": evidence_type.strip(),
                "notes": notes,
            }
            if tracking_info is not None:
                payload_dict["tracking_info"] = tracking_info

            body_bytes = json.dumps(payload_dict, indent=2).encode("utf-8")
            return CompiledEvidencePayload(
                content_type="application/json",
                body_bytes=body_bytes,
                total_size_bytes=len(body_bytes),
            )

        # Mode B: Multipart/form-data with 'input' JSON part and binary file parts
        total_file_size = 0
        validated_files: list[tuple[Path, str, int]] = []

        for path in file_paths:
            if not path.exists():
                raise FileNotFoundError(f"Evidence attachment file not found: {path}")
            if not path.is_file():
                raise MalformedEvidencePartError(f"Evidence path is not a regular file: {path}")

            size = path.stat().st_size
            if size == 0:
                raise UnsupportedMimeTypeError(f"File {path.name} is empty (0 bytes)")
            if size > cls.MAX_FILE_SIZE:
                raise PayloadSizeLimitExceededError("File exceeds 10MB limit")

            total_file_size += size
            if total_file_size > cls.MAX_TOTAL_SIZE:
                raise TotalPayloadSizeExceededError("Cumulative size exceeds 50MB limit")

            mime = cls.inspect_file_mime(path)
            validated_files.append((path, mime, size))

        # Assemble multipart stream
        boundary = f"----DisputeSentryBoundary{uuid.uuid4().hex}"
        parts: list[bytes] = []

        # Part 1: 'input' JSON part
        input_data: dict[str, Any] = {
            "evidence_type": evidence_type.strip(),
            "notes": notes,
        }
        if tracking_info is not None:
            input_data["tracking_info"] = tracking_info

        input_json_bytes = json.dumps(input_data).encode("utf-8")
        input_part_header = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="input"\r\n'
            f"Content-Type: application/json\r\n"
            f"\r\n"
        ).encode()
        parts.append(input_part_header + input_json_bytes + b"\r\n")

        # Part 2..N: Binary file attachments
        for idx, (path, mime, _) in enumerate(validated_files, start=1):
            file_bytes = path.read_bytes()
            file_part_header = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="file{idx}"; filename="{path.name}"\r\n'
                f"Content-Type: {mime}\r\n"
                f"\r\n"
            ).encode()
            parts.append(file_part_header + file_bytes + b"\r\n")

        # Closing boundary
        parts.append(f"--{boundary}--\r\n".encode())

        body_bytes = b"".join(parts)
        content_type = f"multipart/form-data; boundary={boundary}"

        return CompiledEvidencePayload(
            content_type=content_type,
            body_bytes=body_bytes,
            total_size_bytes=total_file_size,
        )
