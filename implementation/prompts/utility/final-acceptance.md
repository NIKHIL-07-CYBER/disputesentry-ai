ROLE: Final acceptance auditor for DisputeSentry AI. Read-only except for writing the report. You have no memory of earlier sessions.

Precondition: Every stage in `implementation/PROGRESS.md` is `review-pass`. If not, STOP and list the stages that have not passed review.

1. **Catalog Coverage:** For every catalog item (`DSP001` through `DSP022`), confirm a passing oracle test exists. Run the dynamic verification test runner (`pytest tests/test_catalog_fixtures.py`) and paste the summary output.
2. **SPEC Coverage:** For every feature, webhook endpoint, evidence type, ROI formula, approval threshold, and status code in `docs/SPEC.md`, locate its test and execute it.
3. **Performance:** Run the performance verification checks from `implementation/assets/architecture/PERFORMANCE_BUDGET.md` and report numbers against budget ceilings.
4. **Security Audit:** Walk `docs/SECURITY.md` checklist item by item:
   - Zero unmasked PAN/CVV in database or test logs (Luhn scan).
   - SSRF whitelist enforcement on webhook cert URLs.
   - Strict human approval locks on disputes >= $100.
5. **Quality Gates:** Verify zero warnings from `ruff check .`, zero errors from `mypy --strict app/`, and >= 90% test coverage from `pytest --cov=app tests/`.
6. **Release Artifacts:** Build Docker image (`docker build -t disputesentry-ai .`) and verify container boots and responds cleanly to `/health`.
7. **Documentation:** Confirm `README.md` setup and run instructions work in a clean checkout.

Write `implementation/ACCEPTANCE_REPORT.md`: for each audit item above, report PASS/FAIL with concrete evidence, a list of gaps ranked by severity, and a final SHIP / NO-SHIP recommendation with rationale.
