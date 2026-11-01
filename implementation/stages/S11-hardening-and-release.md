# S11 System Hardening, Sandbox Validation & Release

## 1 Goal and outcome
Conduct end-to-end sandbox verification, perform zero-PAN data leak audits, containerize the application with `Dockerfile` and `docker-compose.yaml`, and provide judge evaluation documentation in `README.md`.

## 2 Entry conditions
- Stage S10 complete (Dashboard and API operational).
- All previous stages (`S00` to `S10`) passing.

## 3 Read first
1. `docs/CI_RELEASE.md`
2. `docs/VERIFICATION.md`
3. `PROBLEM_STATEMENT.md` §11
4. `implementation/tests/S11-tests.md`

## 4 Files to create or modify
- `Dockerfile`
- `docker-compose.yaml`
- `README.md`
- `run_sandbox_eval.py`
- `tests/integration/test_release_smoke.py`

## 5 Forbidden changes
- Never disable security checks or linter gates to achieve passing build.
- Never commit live production or sandbox secret keys to git.

## 6 Interfaces and signatures
```python
# Standalone evaluation script CLI
# python run_sandbox_eval.py --mode=mock
# python run_sandbox_eval.py --mode=sandbox --client-id=... --secret=...
```

## 7 Step-by-step instructions
1. Create `tests/integration/test_release_smoke.py` running end-to-end sanity tests.
2. Implement `run_sandbox_eval.py`:
   - Runs simulated dispute life cycle across INR, Unauthorised, and SNAD test cases.
   - Asserts 100% catalog fixture conformance.
3. Perform PAN leakage check: scan SQLite database and test logs for 13-19 digit Luhn-valid numbers; assert 0 leaks.
4. Create production `Dockerfile`:
   - Multi-stage build on `python:3.11-slim`.
   - Install dependencies, copy application code, expose port 8000.
   - Run health check instruction `CMD curl -f http://localhost:8000/health || exit 1`.
5. Create `docker-compose.yaml` configuring application container and volume mounts.
6. Write comprehensive `README.md` with:
   - Problem statement & architecture overview.
   - Local setup and one-command run instructions (`uvicorn app.main:app --reload` and `docker-compose up`).
   - Hackathon judge evaluation guide and demo walkthrough.
7. Run complete test suite and linter pass.

## 8 Edge cases
- Running Docker container on systems without network access during evaluation.
- Ensuring seeded SQLite database initializes cleanly on fresh container boot.

## 9 Out of scope
- Post-hackathon enterprise production multi-tenant infrastructure.

## 10 Tests
Follow instructions in `implementation/tests/S11-tests.md`.

## 11 Exit criteria
- 100% of all 22 catalog item fixtures pass in `tests/test_catalog_fixtures.py`.
- `pytest --cov=app tests/` reports $\ge 90\%$ code coverage.
- `ruff check .` and `mypy --strict app/` report zero warnings/errors.
- `docker build -t disputesentry-ai .` builds successfully.

## 12 Commit message
`chore(release): package docker container, add evaluation harness, and author judge documentation`

## 13 Failure and rollback handling
If Docker build fails on dependencies, ensure `pip install --no-cache-dir -r requirements.txt` uses wheels without C compilation errors.

## 14 Common AI-agent pitfalls for this stage
- Omitting instructions for running the application in mock mode without live PayPal credentials.
- Missing `.dockerignore` causing large caches to inflate image size.

## 15 Handoff notes for the next stage
Build complete. Ready for final acceptance review and release.
