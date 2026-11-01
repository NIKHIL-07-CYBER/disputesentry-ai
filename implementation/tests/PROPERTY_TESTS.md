# Property-Based Testing and Invariants

This document outlines property invariants verified using parameterized pytest runs.

---

## 1. Core Invariants

### Invariant 1: Luhn Sanitizer Zero-Leak Guarantee
- **Property:** For any generated random string containing 13 to 19 digit numbers (valid Luhn or invalid Luhn) and 3 to 4 digit CVVs, `sanitize_pci_data(text)` MUST NOT contain any unmasked 13-19 digit number matching the Luhn check.
- **Assertion:** `re.search(r'\b(?:\d[ -]*?){13,19}\b', sanitized_text) is None` for any Luhn-valid substring.

### Invariant 2: Net Expected Recovery Monotonicity
- **Property:** Holding dispute amount $A$, fee $F$, and overhead $C$ constant, $\text{EV}(P_{\text{win}})$ is strictly monotonically increasing with respect to $P_{\text{win}}$.
- **Assertion:** For $P_1 < P_2$, $\text{EV}(P_1) < \text{EV}(P_2)$.

### Invariant 3: Audit Trail Hash Chain Integrity
- **Property:** Given a sequence of $N$ audit entries, recalculating `SHA-256(entry_data + prev_hash)` sequentially from entry 0 to $N-1$ must match the recorded `entry_hash` of each record. Any modification of past records invalidates all subsequent entries.
