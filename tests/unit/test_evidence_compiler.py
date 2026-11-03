"""Unit tests for Evidence Attachment Compiler and Validation (S08, DSP016, DSP017)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
import respx

from app.services.evidence_compiler import (
    CompiledEvidencePayload,
    EvidenceCompiler,
    MalformedEvidencePartError,
    PayloadSizeLimitExceededError,
    TotalPayloadSizeExceededError,
    UnsupportedMimeTypeError,
    detect_mime_type_from_bytes,
)


def _make_dummy_file(
    path: Path,
    header: bytes,
    total_size: int,
    fill_byte: bytes = b"\x00",
) -> Path:
    """Create a temporary test file with the given magic byte header and size."""
    with path.open("wb") as f:
        f.write(header)
        remaining = total_size - len(header)
        if remaining > 0:
            # Write in 64KB chunks to keep memory footprint minimal
            chunk_size = 65536
            chunk = fill_byte * min(remaining, chunk_size)
            written = 0
            while written < remaining:
                to_write = min(len(chunk), remaining - written)
                f.write(chunk[:to_write])
                written += to_write
    return path


class TestEvidenceCompilerUnit:
    """Unit test suite for S08 evidence attachment compiler and validation."""

    def test_t08_01_valid_attachment_compilation(self, tmp_path: Path) -> None:
        """T08-01: Valid PDF + PNG compiles multipart payload and is HTTP 200 ready."""
        pdf_size = int(2.5 * 1024 * 1024)
        png_size = int(1.2 * 1024 * 1024)

        pdf_path = _make_dummy_file(tmp_path / "delivery_receipt.pdf", b"%PDF-1.5\n", pdf_size)
        png_path = _make_dummy_file(
            tmp_path / "damage_photo.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", png_size
        )

        tracking_info = [
            {"carrier_name": "FEDEX", "tracking_number": "9400100000000000000001"}
        ]
        compiled = EvidenceCompiler.validate_and_compile(
            evidence_type="PROOF_OF_DELIVERY",
            notes="Signed delivery receipt and doorstep photo attached.",
            tracking_info=tracking_info,
            file_paths=[pdf_path, png_path],
        )

        assert isinstance(compiled, CompiledEvidencePayload)
        assert compiled.content_type.startswith("multipart/form-data; boundary=")
        boundary = compiled.content_type.split("boundary=")[1].encode("utf-8")
        assert boundary in compiled.body_bytes

        # Check total attachment size
        assert compiled.total_size_bytes == pdf_size + png_size

        # Verify multipart parts
        body_text = compiled.body_bytes.decode("latin1")
        assert 'name="input"' in body_text
        assert 'Content-Type: application/json' in body_text
        assert 'PROOF_OF_DELIVERY' in body_text
        assert '9400100000000000000001' in body_text
        assert 'filename="delivery_receipt.pdf"' in body_text
        assert 'Content-Type: application/pdf' in body_text
        assert 'filename="damage_photo.png"' in body_text
        assert 'Content-Type: image/png' in body_text

        # Verify HTTP 200 readiness by dispatching against mocked PayPal Disputes API endpoint
        with respx.mock(assert_all_called=True) as router:
            mock_route = router.post(
                "https://api-m.sandbox.paypal.com/v1/customer/disputes/PP-D-1234/provide-evidence"
            ).respond(status_code=200, json={"status": "UNDER_REVIEW"})

            client = httpx.Client()
            response = client.post(
                "https://api-m.sandbox.paypal.com/v1/customer/disputes/PP-D-1234/provide-evidence",
                headers={"Content-Type": compiled.content_type},
                content=compiled.body_bytes,
            )
            assert response.status_code == 200
            assert response.json()["status"] == "UNDER_REVIEW"
            assert mock_route.called

    def test_t08_02_single_file_size_limit_exceeded(self, tmp_path: Path) -> None:
        """T08-02: Single file of 10,485,761 bytes (> 10MB) raises PayloadSizeLimitExceededError."""
        oversized = EvidenceCompiler.MAX_FILE_SIZE + 1
        pdf_path = _make_dummy_file(tmp_path / "huge_scan.pdf", b"%PDF-1.4\n", oversized)

        with pytest.raises(PayloadSizeLimitExceededError, match="File exceeds 10MB limit"):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_FULFILLMENT",
                notes="Oversized attachment",
                file_paths=[pdf_path],
            )

    def test_t08_03_cumulative_file_size_exceeded(self, tmp_path: Path) -> None:
        """T08-03: 6 files of 9MB each (54MB total > 50MB) raises TotalPayloadSizeExceededError."""
        file_size = 9 * 1024 * 1024
        file_paths: list[Path] = []
        for i in range(6):
            p = _make_dummy_file(
                tmp_path / f"receipt_part_{i}.pdf", b"%PDF-1.4\n", file_size
            )
            file_paths.append(p)

        with pytest.raises(
            TotalPayloadSizeExceededError, match="Cumulative size exceeds 50MB limit"
        ):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_FULFILLMENT",
                notes="Multiple large attachments totaling 54MB",
                file_paths=file_paths,
            )

    def test_t08_04_unsupported_mime_type_rejection(self, tmp_path: Path) -> None:
        """T08-04: Unsupported file (exe, docx, sh, zip) raises UnsupportedMimeTypeError."""
        exe_path = _make_dummy_file(tmp_path / "invoice.exe", b"MZ\x90\x00\x03\x00", 1024)
        docx_path = _make_dummy_file(tmp_path / "evidence.docx", b"PK\x03\x04\x14\x00", 2048)
        sh_path = _make_dummy_file(tmp_path / "script.sh", b"#!/bin/bash\necho hi", 128)

        for bad_path in [exe_path, docx_path, sh_path]:
            with pytest.raises(
                UnsupportedMimeTypeError, match="Only JPG, PNG, GIF, and PDF allowed"
            ):
                EvidenceCompiler.validate_and_compile(
                    evidence_type="OTHER",
                    notes="Unsupported file upload",
                    file_paths=[bad_path],
                )

    def test_magic_byte_detection_all_allowed_formats(self) -> None:
        """Verify detect_mime_type_from_bytes accurately identifies all permitted MIME types."""
        assert detect_mime_type_from_bytes(b"\x89PNG\r\n\x1a\n\x00\x00") == "image/png"
        assert detect_mime_type_from_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF") == "image/jpeg"
        assert detect_mime_type_from_bytes(b"\xff\xd8\xff\xe1\x10\x20Exif") == "image/jpeg"
        assert detect_mime_type_from_bytes(b"%PDF-1.7\r\n") == "application/pdf"
        assert detect_mime_type_from_bytes(b"GIF87a\x01\x00") == "image/gif"
        assert detect_mime_type_from_bytes(b"GIF89a\x01\x00") == "image/gif"

        # Disallowed formats
        assert detect_mime_type_from_bytes(b"MZ\x90\x00") is None
        assert detect_mime_type_from_bytes(b"PK\x03\x04") is None
        assert detect_mime_type_from_bytes(b"<!DOCTYPE html>") is None
        assert detect_mime_type_from_bytes(b"") is None

    def test_spoofed_file_extension_rejected(self, tmp_path: Path) -> None:
        """Negative case: File named image.png containing plain text is rejected by magic bytes."""
        spoofed = tmp_path / "fake_image.png"
        spoofed.write_text("This is plain ASCII text pretending to be a PNG file.")

        with pytest.raises(UnsupportedMimeTypeError, match="Only JPG, PNG, GIF, and PDF allowed"):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_DELIVERY",
                notes="Fake PNG file",
                file_paths=[spoofed],
            )

    def test_empty_file_rejected(self, tmp_path: Path) -> None:
        """Negative case: Empty file (0 bytes) is rejected."""
        empty = tmp_path / "empty.pdf"
        empty.write_bytes(b"")

        with pytest.raises(UnsupportedMimeTypeError):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_DELIVERY",
                notes="Empty file upload",
                file_paths=[empty],
            )

    def test_missing_evidence_type_raises_malformed_evidence(self) -> None:
        """Negative case: Empty or missing evidence_type raises MalformedEvidencePartError."""
        with pytest.raises(MalformedEvidencePartError, match="evidence_type is required"):
            EvidenceCompiler.validate_and_compile(
                evidence_type="",
                notes="Some notes",
            )

    def test_nonexistent_file_raises_filenotfound(self, tmp_path: Path) -> None:
        """Negative case: File path that does not exist raises FileNotFoundError."""
        ghost = tmp_path / "ghost.pdf"
        with pytest.raises(FileNotFoundError):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_DELIVERY",
                notes="Missing file",
                file_paths=[ghost],
            )

    def test_json_only_mode_when_no_files_provided(self) -> None:
        """Positive case: Tracking-only compilation produces standard application/json payload."""
        tracking = [
            {"carrier_name": "UPS", "tracking_number": "1Z9999999999999999"}
        ]
        compiled = EvidenceCompiler.validate_and_compile(
            evidence_type="PROOF_OF_FULFILLMENT",
            notes="Tracking updated in UPS system.",
            tracking_info=tracking,
            file_paths=None,
        )

        assert compiled.content_type == "application/json"
        assert compiled.total_size_bytes == len(compiled.body_bytes)
        parsed = json.loads(compiled.body_bytes.decode("utf-8"))
        assert parsed["evidence_type"] == "PROOF_OF_FULFILLMENT"
        assert parsed["notes"] == "Tracking updated in UPS system."
        assert parsed["tracking_info"] == tracking

    def test_boundary_exact_max_file_size(self, tmp_path: Path) -> None:
        """Boundary case: File of exactly 10,485,760 bytes (10MB) passes validation."""
        exact_max = EvidenceCompiler.MAX_FILE_SIZE
        exact_file = _make_dummy_file(tmp_path / "exact_10mb.pdf", b"%PDF-1.4\n", exact_max)

        compiled = EvidenceCompiler.validate_and_compile(
            evidence_type="PROOF_OF_DELIVERY",
            notes="Exactly 10MB file",
            file_paths=[exact_file],
        )
        assert compiled.total_size_bytes == exact_max

    def test_boundary_exact_max_cumulative_payload_size(self, tmp_path: Path) -> None:
        """Boundary case: Payload of exactly 52,428,800 bytes (50MB) passes validation."""
        # 5 files of exactly 10MB each = 50MB (52,428,800 bytes)
        size_each = EvidenceCompiler.MAX_FILE_SIZE
        file_paths = [
            _make_dummy_file(tmp_path / f"part_{i}.pdf", b"%PDF-1.4\n", size_each)
            for i in range(5)
        ]

        compiled = EvidenceCompiler.validate_and_compile(
            evidence_type="PROOF_OF_DELIVERY",
            notes="Exactly 50MB total across 5 files",
            file_paths=file_paths,
        )
        assert compiled.total_size_bytes == EvidenceCompiler.MAX_TOTAL_SIZE

    def test_dsp016_fixture_evaluation_good_and_bad(self) -> None:
        """Verify evaluate_size_limits handles DSP016 good and bad metadata scenarios."""
        good_files = [
            {"name": "delivery_receipt.pdf", "size_bytes": 1048576, "mime_type": "application/pdf"},
            {"name": "doorstep_photo.jpg", "size_bytes": 2097152, "mime_type": "image/jpeg"},
        ]
        res_good = EvidenceCompiler.evaluate_size_limits(good_files)
        assert res_good["validation"] == "valid"
        assert res_good["total_size_bytes"] == 3145728
        assert res_good["outcome"] == "upload_permitted"

        bad_files = [
            {
                "name": "huge_uncompressed_scan.pdf",
                "size_bytes": 15728640,
                "mime_type": "application/pdf",
            }
        ]
        res_bad = EvidenceCompiler.evaluate_size_limits(bad_files)
        assert res_bad["validation"] == "invalid"
        assert res_bad["outcome"] == "rejected_locally"
        assert res_bad["error_code"] == "PAYLOAD_TOO_LARGE"
        assert (
            "huge_uncompressed_scan.pdf (15.0 MB exceeds 10 MB limit)"
            in res_bad["oversized_files"]
        )

    def test_dsp017_fixture_evaluation_good_and_bad(self) -> None:
        """Verify evaluate_file_types handles DSP017 good and bad metadata scenarios."""
        good_files = [
            {"filename": "invoice_scan.png", "mime_type": "image/png"},
            {"filename": "postal_receipt.pdf", "mime_type": "application/pdf"},
        ]
        res_good = EvidenceCompiler.evaluate_file_types(good_files)
        assert res_good["validation"] == "valid"
        assert res_good["outcome"] == "formats_accepted"

        bad_files = [
            {"filename": "payload_script.sh", "mime_type": "application/x-sh"},
            {"filename": "archive.zip", "mime_type": "application/zip"},
        ]
        res_bad = EvidenceCompiler.evaluate_file_types(bad_files)
        assert res_bad["validation"] == "invalid"
        assert res_bad["outcome"] == "rejected_locally"
        assert res_bad["error_code"] == "UNSUPPORTED_FILE_TYPE"
        assert "payload_script.sh (application/x-sh)" in res_bad["disallowed_files"]
        assert "archive.zip (application/zip)" in res_bad["disallowed_files"]

    def test_inspect_file_mime_direct(self, tmp_path: Path) -> None:
        """Verify inspect_file_mime handles direct inspection, missing files, and 0-byte files."""
        ghost = tmp_path / "nonexistent.pdf"
        with pytest.raises(FileNotFoundError):
            EvidenceCompiler.inspect_file_mime(ghost)

        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        with pytest.raises(UnsupportedMimeTypeError, match="empty"):
            EvidenceCompiler.inspect_file_mime(empty)

        valid_pdf = _make_dummy_file(tmp_path / "valid.pdf", b"%PDF-1.4\n", 1024)
        assert EvidenceCompiler.inspect_file_mime(valid_pdf) == "application/pdf"

    def test_evaluate_size_limits_cumulative_without_single_oversized(self) -> None:
        """Verify evaluate_size_limits detects cumulative size > 50MB when all files <= 10MB."""
        files = [
            {
                "name": f"chunk_{i}.pdf",
                "size_bytes": 9 * 1024 * 1024,
                "mime_type": "application/pdf",
            }
            for i in range(6)
        ]
        res = EvidenceCompiler.evaluate_size_limits(files)
        assert res["validation"] == "invalid"
        assert res["outcome"] == "rejected_locally"
        assert res["error_code"] == "PAYLOAD_TOO_LARGE"
        assert any("Cumulative payload" in s for s in res["oversized_files"])

    def test_directory_passed_as_file_raises_malformed_evidence(self, tmp_path: Path) -> None:
        """Negative case: Directory path in file_paths raises MalformedEvidencePartError."""
        sub_dir = tmp_path / "not_a_file"
        sub_dir.mkdir()
        with pytest.raises(MalformedEvidencePartError, match="not a regular file"):
            EvidenceCompiler.validate_and_compile(
                evidence_type="PROOF_OF_DELIVERY",
                notes="Passing directory as file",
                file_paths=[sub_dir],
            )

    def test_empty_file_error_direct_instantiation(self) -> None:
        """Verify EmptyFileError class instantiation and error code."""
        from app.services.evidence_compiler import EmptyFileError

        err = EmptyFileError("Custom empty file error")
        assert err.error_code == "EMPTY_FILE"
        assert str(err) == "Custom empty file error"

