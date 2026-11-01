# S08 Evidence Attachment Compiler & Validation

## 1 Goal and outcome
Implement `app/services/evidence_compiler.py` to validate document attachments against PayPal size limits ($\le 10\text{ MB}$ per file, $\le 50\text{ MB}$ total, `DSP016`) and permitted MIME types (`image/jpeg`, `image/png`, `application/pdf`, `DSP017`), compiling multi-part payloads for PayPal Disputes API submission.

## 2 Entry conditions
- Stage S07 complete (`DSP013`, `DSP015`, `DSP018` passing).

## 3 Read first
1. `catalog/DSP016.yaml`, `catalog/DSP017.yaml`
2. `docs/SPEC.md` §4.2.3
3. `implementation/assets/flows/EVIDENCE_COMPILATION_FLOW.md`
4. `implementation/assets/reference/EDGE_CASES.md`
5. `implementation/tests/S08-tests.md`

## 4 Files to create or modify
- `app/services/evidence_compiler.py`
- `tests/unit/test_evidence_compiler.py`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- Never submit unverified file types or oversized payloads to PayPal API.

## 6 Interfaces and signatures
```python
from pathlib import Path

class CompiledEvidencePayload:
    content_type: str
    body_bytes: bytes
    total_size_bytes: int

class EvidenceCompiler:
    MAX_FILE_SIZE: int = 10 * 1024 * 1024       # 10 MB
    MAX_TOTAL_SIZE: int = 50 * 1024 * 1024      # 50 MB
    ALLOWED_MIMES: set[str] = {"image/jpeg", "image/png", "image/gif", "application/pdf"}

    @classmethod
    def validate_and_compile(
        cls,
        evidence_type: str,
        notes: str,
        tracking_info: list[dict] | None = None,
        file_paths: list[Path] | None = None
    ) -> CompiledEvidencePayload: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP016` | `catalog/fixtures/DSP016/` | Enforce max 10MB per file and max 50MB cumulative payload size | Reject oversized files with PayloadSizeLimitExceededError before upload | `applies_when`, `expected.outcome` |
| `DSP017` | `catalog/fixtures/DSP017/` | Enforce MIME whitelist strictly to JPG, PNG, GIF, and PDF via magic bytes | Inspect header magic bytes; reject executables or docs with UnsupportedMimeTypeError | `applies_when`, `correct_alternative` |

## 8 Step-by-step instructions
1. Write tests in `tests/unit/test_evidence_compiler.py` per `S08-tests.md`. Verify they fail.
2. Implement `app/services/evidence_compiler.py`:
   - Inspect magic bytes of input files (`\x89PNG\r\n\x1a\n`, `\xff\xd8\xff`, `%PDF-`, `GIF8`).
   - If magic bytes do not match allowed MIME types, raise `UnsupportedMimeTypeError`.
   - Measure byte sizes: if any file exceeds 10,485,760 bytes, raise `PayloadSizeLimitExceededError`.
   - If sum of file sizes exceeds 52,428,800 bytes, raise `TotalPayloadSizeExceededError`.
   - If files provided, assemble multipart/form-data payload with `input` JSON part and file parts.
   - If only tracking provided, assemble standard application/json payload.
3. Run tests until 100% green.

## 9 Edge cases
- File named `.png` containing plain ASCII or HTML bytes must be rejected.
- File of exactly 10,485,760 bytes must be accepted.

## 10 Out of scope
- AI decision reasoning (handled in S09).

## 11 Tests
Follow instructions in `implementation/tests/S08-tests.md`. Connect `DSP016`, `DSP017` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Unit tests in `test_evidence_compiler.py` pass 100%.
- Catalog fixtures `DSP016`, `DSP017` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(evidence): implement evidence attachment size validation, magic byte mime verification, and multipart encoding (DSP016, DSP017)`

## 14 Failure and rollback handling
If MIME detection fails on valid fixtures, verify that buffer read for magic bytes does not seek or truncate the file before encoding.

## 15 Handoff notes for the next stage
Provides attachment formatting for S09 (AI Reasoning Shielding).
