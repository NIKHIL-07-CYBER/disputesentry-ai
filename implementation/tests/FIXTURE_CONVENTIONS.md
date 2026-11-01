# Fixture Conventions and Layout

This document defines the naming standards, directory structure, and format rules for test fixtures.

---

## 1. Directory Structure

Every behavior catalog item has an identical directory layout under `catalog/fixtures/`:

```
catalog/fixtures/DSP###/
├── good.json        # Valid, authentic input representing the target behavior
├── bad.json         # Tampered, malformed, or boundary-violating input
└── expected.yaml    # Oracle assertion specification
```

---

## 2. Assertion Schema (`expected.yaml`)

```yaml
id: DSP###
outcome: "VERIFIED"
status_code: 200
expected_fields:
  status: "success"
  recommended_action: "CONTEST"
expected_error: null
```

---

## 3. Dynamic Pytest Fixture Loading

Pytest fixtures in `tests/conftest.py` must load fixture files via deterministic relative paths:
```python
import json
import yaml
from pathlib import Path

def load_catalog_fixture(catalog_id: str, fixture_type: str = "good") -> dict:
    base_path = Path(__file__).parent.parent / "catalog" / "fixtures" / catalog_id
    if fixture_type == "expected":
        with open(base_path / "expected.yaml", "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    with open(base_path / f"{fixture_type}.json", "r", encoding="utf-8") as f:
        return json.load(f)
```
