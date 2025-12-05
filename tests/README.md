# tklr Test Suite

This directory contains the test suite for tklr, organized using pytest.

## Running Tests

### Run all tests
```bash
pytest
```

### Run tests with coverage report
```bash
pytest --cov=src/tklr --cov-report=html
```

### Run specific test file
```bash
pytest tests/test_item_parsing.py
```

### Run specific test class or function
```bash
pytest tests/test_item_parsing.py::TestBasicParsing
pytest tests/test_item_parsing.py::TestBasicParsing::test_simple_task
```

### Run only unit tests
```bash
pytest -m unit
```

### Run only integration tests
```bash
pytest -m integration
```

### Run tests in verbose mode
```bash
pytest -v
```

### Run tests and stop at first failure
```bash
pytest -x
```

## Test Organization

### Test Files

- `test_item_parsing.py` - Basic parsing of item types, priorities, descriptions, bins
- `test_item_dates.py` - Date/datetime parsing, timezone handling, extents
- `test_item_recurrence.py` - Repeating items, rrules, rdates
- `test_item_finish_offset.py` - Finished items, offset/postponement logic
- `test_item_alerts.py` - Alert and notification parsing
- `test_item_goals.py` - Goal items and tracking
- `test_integration_database.py` - Database operations and integration tests

### Fixtures (conftest.py)

Common fixtures available in all tests:

- `frozen_time` - Control time during tests (use with `frozen_time.freeze("2025-01-01 10:00:00")`)
- `test_env` - Clean TklrEnvironment for testing
- `temp_db_path` - Temporary database path (auto-cleanup)
- `test_controller` - Controller with fresh test database
- `item_factory` - Function to create Item instances easily
- `sample_items` - Dictionary of common test entry strings
- `populated_controller` - Controller with database populated with sample items
- `mock_now` - Freezes time to standard test datetime
- `overdue_context` - Time context for overdue testing
- `future_context` - Time context for upcoming items testing

## Time Simulation

Tests use `freezegun` to simulate different times:

```python
def test_overdue_task(frozen_time, item_factory):
    frozen_time.freeze("2025-01-15 12:00:00")

    item = item_factory("~ task @s 2025-01-14")

    # Test item behavior as if it's Jan 15, 2025
    assert item.is_overdue()  # Task from yesterday
```

You can also move time forward:

```python
def test_time_progression(frozen_time, item_factory):
    frozen_time.freeze("2025-01-15 09:00:00")

    item = item_factory("~ task @s 2025-01-15 10:00")

    # Move time forward
    frozen_time.tick(delta=timedelta(hours=2))

    # Now it's 11:00, task should be past due
```

## Writing New Tests

### Basic Test Structure

```python
import pytest
from datetime import datetime

@pytest.mark.unit
class TestMyFeature:
    """Test description."""

    def test_something(self, item_factory, frozen_time):
        """Test a specific behavior."""
        frozen_time.freeze("2025-01-15 12:00:00")

        item = item_factory("~ task @s 2025-01-15")

        assert item.parse_ok
        assert item.itemtype == "~"
```

### Using the item_factory

```python
def test_with_factory(item_factory):
    # Simple creation
    item = item_factory("~ task @p 1")

    assert item.parse_ok
    assert item.priority == 1
```

### Testing Database Operations

```python
@pytest.mark.integration
def test_database_operation(test_controller, item_factory):
    item = item_factory("~ task")

    record_id = test_controller.add_item(item)

    assert record_id > 0
```

## Regression Testing

When fixing a bug:

1. Write a test that reproduces the bug
2. Verify the test fails
3. Fix the bug
4. Verify the test passes
5. The test now prevents regression

Example:

```python
def test_bug_timezone_naive_handling(item_factory):
    """Regression test for issue #123 where naive times were treated as UTC."""
    item = item_factory("* noon meeting @s 12p z none")

    assert item.parse_ok
    assert item.timezone is None  # Should be naive
    assert item.start_time.hour == 12  # Should be noon local time
```

## Continuous Integration

Tests should be run:
- Before committing changes
- In CI/CD pipeline
- Before creating pull requests

The pre-commit hook (see main README) will run tests automatically.
