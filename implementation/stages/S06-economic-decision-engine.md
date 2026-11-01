# S06 Economic Decision & Net Recovery ROI Engine

## 1 Goal and outcome
Implement the Net Expected Recovery ($\text{EV}$) formula in `app/domain/economics.py` (`DSP011`), the inquiry stage messaging and settlement offer generator (`DSP012`), and the historical audit metrics service calculating win rate vs net recovery (`DSP021`).

## 2 Entry conditions
- Stage S05 complete (`DSP007` - `DSP009` passing).

## 3 Read first
1. `catalog/DSP011.yaml`, `catalog/DSP012.yaml`, `catalog/DSP021.yaml`
2. `docs/SPEC.md` §3
3. `implementation/assets/flows/EVALUATION_AND_DECISION_FLOW.md`
4. `implementation/tests/S06-tests.md`

## 4 Files to create or modify
- `app/domain/economics.py`
- `app/services/metrics_service.py`
- `tests/unit/test_economics.py`
- `tests/unit/test_metrics_service.py`

## 5 Forbidden changes
- Never modify files in `catalog/` or `docs/`.
- No floating point division by zero or unbounded numbers.

## 6 Interfaces and signatures
```python
from app.domain.models import RecommendedAction

class EconomicDecision:
    expected_value: float
    recommended_action: RecommendedAction
    break_even_win_probability: float
    justification: str

class EconomicEngine:
    def __init__(self, standard_fee: float = 15.0, labor_cost: float = 5.0): ...
    def evaluate(self, amount: float, win_probability: float, stage: str) -> EconomicDecision: ...

class MetricsService:
    async def compute_recovery_metrics(self) -> dict[str, float]: ...
```

## 7 Catalog Items Covered

| ID | Fixture Path | Expected Outcome | Correct-Alternative Summary | Driving Catalog Fields |
|---|---|---|---|---|
| `DSP011` | `catalog/fixtures/DSP011/` | Compute Net Expected Recovery; recommend CONTEST if EV > 0, CONCEDE if EV <= 0 | Apply EV = (P_win * A) - ((1 - P_win) * F) - C; recommend action based on sign | `applies_when`, `expected.outcome` |
| `DSP012` | `catalog/fixtures/DSP012/` | Formulate inquiry offer or message to resolve before claim escalation | If stage == INQUIRY and amount < threshold, recommend INQUIRY_OFFER | `applies_when`, `correct_alternative` |
| `DSP021` | `catalog/fixtures/DSP021/` | Compute win rate and net recovery metrics over historical dispute records | Aggregate won vs lost disputes; compute net dollar recovery rate | `applies_when`, `expected.outcome` |

## 8 Step-by-step instructions
1. Write tests in `tests/unit/test_economics.py` and `tests/unit/test_metrics_service.py` per `S06-tests.md`. Verify they fail.
2. Implement `app/domain/economics.py`:
   - Calculate $\text{EV} = (P_{\text{win}} \cdot A) - ((1 - P_{\text{win}}) \cdot F) - C$.
   - Calculate break-even probability: $P_{\text{break\_even}} = (F + C) / (A + F)$.
   - If $\text{EV} > 0$: recommend `CONTEST`.
   - If $\text{EV} \le 0$: recommend `CONCEDE`.
   - If `stage == "INQUIRY"` and partial refund is appropriate: recommend `INQUIRY_OFFER`.
3. Implement `app/services/metrics_service.py`:
   - Query resolved disputes in SQLite store.
   - Calculate win rate: $\text{Won} / \text{Total}$.
   - Calculate net recovery: $\sum \text{Recovered Dollars} / \sum \text{Total Disputed Dollars}$.
4. Run tests until 100% green.

## 9 Edge cases
- Zero dollar dispute ($A = 0.0$): breaks even at impossible probability; recommends concede.
- Extremely high dispute amount ($A = \$10,000.00$): ensure no float overflow.

## 10 Out of scope
- Operator approval gate enforcement (handled in S07).

## 11 Tests
Follow instructions in `implementation/tests/S06-tests.md`. Connect `DSP011`, `DSP012`, `DSP021` in `tests/test_catalog_fixtures.py`.

## 12 Exit criteria
- Unit tests in `test_economics.py` and `test_metrics_service.py` pass 100%.
- Catalog fixtures `DSP011`, `DSP012`, `DSP021` pass in fixture runner.
- `ruff check app/ tests/` and `mypy --strict app/` pass.

## 13 Commit message
`feat(economics): implement net expected recovery roi engine and historical recovery metrics (DSP011, DSP012, DSP021)`

## 14 Failure and rollback handling
If mathematical tests fail, check precision rounding (`round(val, 2)`).

## 15 Handoff notes for the next stage
Provides recommendations and financial calculations for S07 (Approval Gate and Safe Fallbacks).
