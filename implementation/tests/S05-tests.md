# S05 tests: Seller Protection Rule Engine

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T05-01` | INR delivery verified (`DSP007`) | Input from `catalog/fixtures/DSP007/good.json` (carrier status `DELIVERED`, address matched) | `ProtectionEligibility.ELIGIBLE`, `recommended_action: CONTEST`, $P_{\text{win}} \ge 0.90$ |
| `T05-02` | INR not delivered (`DSP007`) | Input from `catalog/fixtures/DSP007/bad.json` (carrier status `PRE_TRANSIT`) | `ProtectionEligibility.INELIGIBLE`, `recommended_action: CONCEDE`, $P_{\text{win}} \le 0.05$ |
| `T05-03` | Unauthorised payment prior ship (`DSP008`) | Input from `catalog/fixtures/DSP008/good.json` (ship date 2026-10-30, dispute 2026-11-01) | `ProtectionEligibility.ELIGIBLE`, `recommended_action: CONTEST`, $P_{\text{win}} \ge 0.85$ |
| `T05-04` | Unauthorised payment late ship (`DSP008`) | Input from `catalog/fixtures/DSP008/bad.json` (ship date 2026-11-02, dispute 2026-11-01) | `ProtectionEligibility.INELIGIBLE`, `recommended_action: CONCEDE` |
| `T05-05` | SNAD return policy match (`DSP009`) | Input from `catalog/fixtures/DSP009/good.json` (prior full refund record exists) | `ProtectionEligibility.ELIGIBLE`, `evidence_type: PROOF_OF_REFUND`, $P_{\text{win}} \ge 0.95$ |

## Positive cases
- Matches delivery status `DELIVERED` with recipient postal code verification.
- Supports major carrier tracking formats (USPS, UPS, FedEx, DHL).

## Negative cases
- Mismatched postal code triggers `INELIGIBLE` for INR claims.
- Missing shipment date triggers `INELIGIBLE` for Unauthorised claims.

## Boundary cases
- Item shipped on exact same hour as dispute notification (treated as eligible if timestamp is prior).

## Fixtures and golden files used
- `catalog/fixtures/DSP007/`
- `catalog/fixtures/DSP008/`
- `catalog/fixtures/DSP009/`

## Commands to run (exact)
```bash
pytest tests/unit/test_seller_protection.py -v
```

## Coverage target
- 100% line and branch coverage of `app/domain/seller_protection.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Case-sensitive comparison of carrier status strings (e.g., comparing `"delivered"` instead of normalizing to `"DELIVERED"`).
- Omitting postal code prefix validation when delivery address spans ZIP+4 format.
