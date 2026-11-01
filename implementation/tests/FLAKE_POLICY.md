# Zero-Flake Policy and Quarantine Protocol

Flaky tests erode confidence in automated verification. DisputeSentry AI enforces a zero-tolerance policy for test non-determinism.

---

## 1. Zero-Flake Rules

1. **No External Network Calls:** Any test that makes a real HTTP request outside `localhost` or sandbox verification suites is immediately rejected.
2. **Deterministic Time:** Tests involving timestamps must use frozen clocks (`pytest-mock` or explicit dependency injection) rather than `datetime.utcnow()`.
3. **No Unbounded Sleep:** `asyncio.sleep()` or `time.sleep()` is forbidden in unit and integration tests. Use event synchronization (`asyncio.Event`) where concurrency is verified.

---

## 2. Quarantine Procedure

- If a test exhibits non-deterministic failure across 10 repeat executions (`pytest --count=10`):
  1. The test is quarantined in `tests/quarantine/`.
  2. The issue is recorded in `docs/OPEN_QUESTIONS.md`.
  3. The build is marked blocked until root cause is identified and patched.
