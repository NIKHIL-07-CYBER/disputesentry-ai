# Evidence Attachment Compilation and Validation Flow

This document specifies the validation, MIME type inspection, size constraint enforcement, and payload encoding executed by `app/services/evidence_compiler.py`.

---

## 1. Flow Diagram

```mermaid
flowchart TD
    Start[Compile Evidence Package] --> CheckMode{Payload Type Required}
    
    CheckMode -->|Tracking Only| JsonMode[Encode Application/JSON Payload]
    CheckMode -->|Files & Documents| FileLoop[Iterate Document Attachments]
    
    FileLoop --> SizeCheck{File Size <= 10 MB?}
    SizeCheck -->|No| RejectSize[Raise PayloadSizeLimitExceededError]
    SizeCheck -->|Yes| MimeCheck{MIME in [image/png, image/jpeg, application/pdf]?}
    
    MimeCheck -->|No| RejectMime[Raise UnsupportedMimeTypeError]
    MimeCheck -->|Yes| CumulSizeCheck{Cumulative Size <= 50 MB?}
    
    CumulSizeCheck -->|No| RejectTotal[Raise TotalPayloadSizeExceededError]
    CumulSizeCheck -->|Yes| EncodePart[Add MIME Part to Multipart Stream]
    
    EncodePart --> MoreFiles{More Files?}
    MoreFiles -->|Yes| FileLoop
    MoreFiles -->|No| BuildInputJson[Generate 'input' Metadata JSON Part]
    
    BuildInputJson --> AssembleMultipart[Assemble Final Multipart/Form-Data Payload]
    AssembleMultipart --> Ready[Ready for PayPal Disputes API POST]
    JsonMode --> Ready
```

---

## 2. Constraints & Validation Matrix

| Parameter | Constraint | Error Raised on Violation |
|---|---|---|
| **Per-File Size** | $\le 10,485,760\text{ bytes}$ ($10\text{ MB}$) | `PayloadSizeLimitExceededError` |
| **Cumulative Request Size** | $\le 52,428,800\text{ bytes}$ ($50\text{ MB}$) | `TotalPayloadSizeExceededError` |
| **Allowed File Types** | `image/jpeg`, `image/png`, `application/pdf`, `image/gif` | `UnsupportedMimeTypeError` |
| **Multipart Structure** | Must include `input` JSON part describing evidence | `MalformedEvidencePartError` |
