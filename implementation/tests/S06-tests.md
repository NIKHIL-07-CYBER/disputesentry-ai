# S06 tests: Economic Decision & Net Recovery ROI Engine

## Write these BEFORE implementation

| Test ID | Name | Input (concrete) | Expected (concrete) |
|---|---|---|---|
| `T06-01` | Positive ROI contest recommendation (`DSP011`) | $A = \$150.00$, $P_{\text{win}} = 0.85$, $F = \$15.00$, $C = \$5.00$ | $\text{EV} = (0.85 \cdot 150) - (0.15 \cdot 15) - 5 = 120.25 > 0$, `recommended_action: CONTEST` |
| `T06-02` | Negative ROI concede recommendation (`DSP011`) | $A = \$10.00$, $P_{\text{win}} = 0.30$, $F = \$15.00$, $C = \$5.00$ | $\text{EV} = (0.30 \cdot 10) - (0.70 \cdot 15) - 5 = -12.50 \le 0$, `recommended_action: CONCEDE` |
| `T06-03` | Inquiry stage settlement offer (`DSP012`) | Stage is `INQUIRY`, amount $\$40.00$, customer requests partial compensation | `recommended_action: INQUIRY_OFFER`, offer amount $\$20.00$ |
| `T06-04` | Audit metrics calculation (`DSP021`) | 10 resolved disputes (6 won, 4 conceded/lost) | Returns `win_rate = 0.60`, `net_recovery_rate`, `total_saved_usd` |

## Positive cases
- Mathematical calculation matches exact dollar precision.
- Configurable fee $F$ and labor cost $C$ from `config.yaml` are applied.

## Negative cases
- Negative dispute amount $A < 0$ raises `ValueError`.
- $P_{\text{win}}$ outside $[0.0, 1.0]$ raises `ValueError`.

## Boundary cases
- Exactly zero expected value ($\text{EV} = 0.00$) defaults to `CONCEDE` to prevent unprofitable labor expenditure.

## Fixtures and golden files used
- `catalog/fixtures/DSP011/`
- `catalog/fixtures/DSP012/`
- `catalog/fixtures/DSP021/`

## Commands to run (exact)
```bash
pytest tests/unit/test_economics.py tests/unit/test_metrics_service.py -v
```

## Coverage target
- 100% coverage of `app/domain/economics.py` and `app/services/metrics_service.py`.

## Regression traps (mistakes an AI agent is likely to make in this stage)
- Floating point rounding errors causing imprecise comparison around 0.0.
- Forgetting to factor non-refundable dispute fee into expected loss.
