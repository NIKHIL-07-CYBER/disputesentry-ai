ROLE: Quantitative financial systems engineer implementing the ROI decision engine for DisputeSentry AI. You have no memory of earlier sessions.

TASK: Execute stage S06 (Economic Decision & Net Recovery ROI Engine) of DisputeSentry AI.
- Source of truth: `implementation/stages/S06-economic-decision-engine.md`
- Test instructions: `implementation/tests/S06-tests.md`
- Router: `implementation/MASTER.md`
- Catalog Items: `DSP011`, `DSP012`, `DSP021`

PRE-FLIGHT:
1. Read `implementation/MASTER.md`, `AGENTS.md`, `implementation/stages/S06-economic-decision-engine.md`, and `implementation/tests/S06-tests.md`.
2. Read Section 3 ("Read first") of the stage file in order.
3. Confirm `implementation/PROGRESS.md` shows S05 as `review-pass`.
4. Verify catalog fixtures for `DSP011`, `DSP012`, and `DSP021` exist.
5. Run baseline test suite to confirm previous stages remain green.
Print results before modifying files.

SCOPE FENCE:
- Allowed paths: Modify ONLY files listed in Section 4 of `implementation/stages/S06-economic-decision-engine.md` (`app/domain/economics.py`, `app/services/metrics_service.py`, `tests/unit/test_economics.py`, `tests/unit/test_metrics_service.py`).
- Strictly forbidden: Never hardcode financial thresholds outside `config.yaml`. Never edit `catalog/` or `docs/`.

METHOD:
1. Review pitfalls in Section 14 of `implementation/stages/S06-economic-decision-engine.md`.
2. Write unit tests first in `tests/unit/test_economics.py` and `tests/unit/test_metrics_service.py` per `S06-tests.md`. Verify they fail.
3. Implement an item only after its unit test and oracle test exist.
4. Implement `app/domain/economics.py` calculating $\text{EV} = (P_{\text{win}} \cdot A) - ((1 - P_{\text{win}}) \cdot F) - C$, break-even threshold, and inquiry messaging recommendations.
5. Implement `app/services/metrics_service.py` aggregating win rates and net recovery.
6. Connect `DSP011`, `DSP012`, `DSP021` to `tests/test_catalog_fixtures.py`.
7. If the oracle disagrees with the catalog, STOP and use `blocked-triage`. Never edit a test to match the code.

EXIT CRITERIA:
Execute the exact commands in Section 11 of `implementation/stages/S06-economic-decision-engine.md`:
```bash
pytest tests/unit/test_economics.py tests/unit/test_metrics_service.py
pytest tests/test_catalog_fixtures.py -k "DSP011 or DSP012 or DSP021"
ruff check app/ tests/
mypy --strict app/
```
Paste real terminal output. Verify all three catalog items pass.

CLOSE-OUT:
1. Update `implementation/PROGRESS.md`: set S06 to `implemented`, record today's date, commit hash, and summary notes.
2. Commit changes with the exact commit message from Section 12:
`feat(economics): implement net expected recovery roi engine and historical recovery metrics (DSP011, DSP012, DSP021)`

STOP CONDITIONS:
Stop immediately if floating point calculations produce negative zero or boundary discrepancies. Follow `implementation/MASTER.md`.

FINAL REPORT:
Print files created/modified, tests added, exit-command output, deviations (none), and next stage ID (`S07`).
