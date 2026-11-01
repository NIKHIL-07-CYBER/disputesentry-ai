# S08 tests: Evidence Attachment Compiler & Validation

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T08-01` | Valid attachment compilation (`DSP016`, `DSP017`) | PDF file ($2.5\text{ MB}$) + PNG image ($1.2\text{ MB}$) | Compiles multipart payload; returns HTTP 200 ready |
| `T08-02` | Single file size limit exceeded (`DSP016`) | Single file of $10,485,761\text{ bytes}$ ($> 10\text{ MB}$) | Raises `PayloadSizeLimitExceededError("File exceeds 10MB limit")` |
| `T08-03` | Cumulative file size exceeded (`DSP016`) | 6 valid files of $9\text{ MB}$ each ($54\text{ MB}$ total) | Raises `TotalPayloadSizeExceededError("Cumulative size exceeds 50MB limit")` |
| `T08-04` | Unsupported MIME type rejection (`DSP017`) | File `invoice.exe` or `evidence.docx` | Raises `UnsupportedMimeTypeError("Only JPG, PNG, GIF, and PDF allowed")` |

## Positive cases
- Magic byte validation matches PNG (`\x89PNG\r\n\x1a\n`), JPEG (`\xff\xd8\xff`), and PDF (`%PDF-`).
- Multi-part encoder adds proper Content-Disposition and Content-Type headers per part.

## Negative cases
- File named `image.png` containing plain text bytes is rejected as invalid image.
- Empty file (0 bytes) is rejected.

## Boundary cases
- File of exactly $10,485,760\text{ bytes}$ passes validation.
- Payload of exactly $52,428,800\text{ bytes}$ passes validation.

## Fixtures and golden files used
- `catalog/fixtures/DSP016/`
- `catalog/fixtures/DSP017/`

## Commands to run (exact)
```bash
pytest tests/unit/test_evidence_compiler.py -v
```

## Coverage target
- 95%+ coverage across `app/services/evidence_compiler.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Relying on file extensions rather than magic byte inspection.
- Buffering massive multipart payloads in memory twice, causing OOM spikes.
