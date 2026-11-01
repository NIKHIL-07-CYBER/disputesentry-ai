# Catalog Item Test Recipe

This document provides the standard four-step procedure for verifying any catalog item (`DSP###`).

---

## The 4-Step Recipe

### Step 1: Fixture Inspection
- Locate `catalog/fixtures/DSP###/` directory.
- Confirm presence of `good.json` (or valid input payload), `bad.json` (or invalid / tampered input), and `expected.yaml` (ground truth assertions).

### Step 2: Unit Test Construction
- Create or update the unit test module under `tests/unit/` corresponding to the domain module.
- Write tests exercising the component with `good.json` and `bad.json` inputs.

### Step 3: Oracle Test Execution
- The automated runner `tests/test_catalog_fixtures.py` dynamically loads the fixture directory.
- It invokes the component and verifies that:
  1. The output status matches `expected.outcome`.
  2. Any error raised matches `expected.severity_default`.
  3. The return data matches `expected.fields`.

### Step 4: Golden Verification & Diff Check
- Validate that the output matches the golden structure recorded in `expected.yaml`.
- Ensure zero hardcoded bypasses or test-only shortcuts exist in production code.
