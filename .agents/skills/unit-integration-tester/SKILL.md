---
name: unit-integration-tester
description: Test-Driven Development (TDD), Pytest fixtures, test mocks, end-to-end integration tests, and code coverage analysis.
---

# Unit & Integration Tester Skill

Methodologies for creating resilient test suites, mocking external APIs, and ensuring high test coverage.

## Pytest Best Practices

### 1. Test Discovery & Organization
* Test files named `test_*.py` under `tests/`.
* Test functions named `def test_<behavior>():`.

### 2. Fixtures & Mocks (`tests/conftest.py`)
```python
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture
def mock_tracker():
    tracker = MagicMock()
    tracker.get_slot.return_value = "Delhi"
    tracker.latest_message = {"text": "What is the weather in Delhi?"}
    return tracker

@pytest.fixture
def mock_dispatcher():
    return MagicMock()
```

### 3. Running Test Suites
```bash
# Run all tests with verbose output
/home/ubuntu/rasa-env/bin/pytest tests/ -v

# Run with coverage report
/home/ubuntu/rasa-env/bin/pytest --cov=actions tests/ --cov-report=term-missing
```
