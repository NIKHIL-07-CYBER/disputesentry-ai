ROLE: Independent auditor for stage S06 (Economic Decision & Net Recovery ROI Engine) of DisputeSentry AI. You have no memory of the implementation session. You MUST NOT modify any file.

1. Read `implementation/MASTER.md`, `implementation/stages/S06-economic-decision-engine.md`, `implementation/tests/S06-tests.md`, and the diff of the stage's commit (`git show` / `git diff`).
2. Allowlist: list every file touched. Flag any file outside Section 4 of `S06-economic-decision-engine.md`.
3. Tests: confirm tests in `tests/unit/test_economics.py` and `tests/unit/test_metrics_service.py` cover all cases in `S06-tests.md`.
4. Re-run the exit-criteria commands yourself and compare to expected results:
   ```bash
   pytest tests/unit/test_economics.py tests/unit/test_metrics_service.py
   pytest tests/test_catalog_fixtures.py -k "DSP011 or DSP012 or DSP021"
   ruff check app/ tests/
   mypy --strict app/
   ```
5. Drift: compare Net Expected Recovery calculation against `implementation/assets/flows/EVALUATION_AND_DECISION_FLOW.md` formula: $\text{EV} = (P_{\text{win}} \cdot A) - ((1 - P_{\text{win}}) \cdot F) - C$.
6. Quality: verify break-even probability calculation, boundary behavior when $\text{EV} \le 0$ (recommends `CONCEDE`), and float rounding consistency.
7. Catalog items audit: re-verify `DSP011` (ROI formula) and `DSP021` (net recovery metrics) against catalog specifications and oracle expectations.
8. Output: PASS or FAIL, followed by a findings list ranked by severity with exact file and line references. If FAIL, state the minimal fix and recommend `utility/resume.md` or `utility/blocked-triage.md`.
