# Testing Cheat Sheet

Quick reference for common testing patterns in tklr.

## Basic Test Structure

```python
import pytest

@pytest.mark.unit
def test_something(item_factory):
    """Test description."""
    # Arrange
    item = item_factory("~ task @s 2025-01-15 @p 1")

    # Act (if needed)
    # result = item.some_method()

    # Assert
    assert item.parse_ok, f"Parse failed: {item.parse_message}"
    assert item.priority == 1
```

## Time Simulation

```python
def test_with_time(item_factory, frozen_time):
    """Test with controlled time."""
    # Use freeze_time context manager
    with freeze_time("2025-01-15 12:00:00"):
        item = item_factory("~ task @s 2025-01-15")
        assert item.parse_ok

        # Move time forward if needed
        with freeze_time("2025-01-16 12:00:00"):
            # Now it's the next day
            pass
```

## Database Tests

```python
@pytest.mark.integration
def test_database(test_controller, item_factory):
    """Test database operations."""
    item = item_factory("~ task @s 2025-01-15 @p 1")

    assert item.parse_ok

    # Add to database
    record_id = test_controller.add_item(item)

    assert record_id > 0
```

## Item Attributes

Based on actual Item class:

```python
def test_item_attributes(item_factory):
    """Common Item attributes."""
    item = item_factory("~ task @s 2025-01-15 @p 1 @d Description")

    # Parsing
    assert item.parse_ok              # True if parsed successfully
    assert item.parse_message         # Error message if failed

    # Basic attributes
    assert item.itemtype == "~"       # Item type character
    assert item.subject               # Item summary/subject
    assert item.priority == 1         # Priority level
    assert item.description           # Description text
    assert item.context               # Context string

    # Date/time
    assert item.dtstart               # Start datetime
    assert item.timezone              # Timezone info

    # Collections
    assert isinstance(item.bin_paths, list)      # Bin paths
    assert isinstance(item.rdates, list)    # Recurrence dates
    assert isinstance(item.alerts, list)    # Alert list
```

## Common Assertions

```python
# Parsing succeeded
assert item.parse_ok, f"Parse failed: {item.parse_message}"

# Parsing failed (for error testing)
assert not item.parse_ok
assert "error message" in item.parse_message.lower()

# String containment
assert "expected text" in item.subject
assert "description" in item.description

# Type checks
assert item.itemtype == "~"    # Task
assert item.itemtype == "*"    # Event
assert item.itemtype == "%"    # Note
assert item.itemtype == "!"    # Goal
assert item.itemtype == "^"    # Project

# Numeric comparisons
assert item.priority == 1
assert item.priority is None  # No priority set

# List/collection checks
assert len(item.bin_paths) > 0
assert "work/projects" in item.bin_paths
assert isinstance(item.rdates, list)
```

## Fixtures Quick Reference

```python
# item_factory - Create items easily
def test_factory(item_factory):
    item = item_factory("~ task @s 2025-01-15")

# frozen_time - Control time
def test_time(frozen_time):
    with freeze_time("2025-01-15 12:00:00"):
        # Time is now frozen

# test_controller - Fresh database
def test_db(test_controller, item_factory):
    item = item_factory("~ task")
    test_controller.add_item(item)

# test_env - Clean environment
def test_env_usage(test_env, item_factory):
    item = item_factory("~ task")

# sample_items - Pre-defined test cases
def test_samples(sample_items, item_factory):
    for name, entry in sample_items.items():
        item = item_factory(entry)
        # Test each sample
```

## Parametrized Tests

Test multiple inputs:

```python
@pytest.mark.parametrize("priority,expected", [
    (1, "highest"),
    (2, "high"),
    (3, "medium"),
    (4, "low"),
    (5, "lowest"),
])
def test_priorities(item_factory, priority, expected):
    """Test multiple priority levels."""
    item = item_factory(f"~ task @p {priority}")
    assert item.parse_ok
    assert item.priority == priority
```

## Test Entry Strings

Common patterns for entry strings:

```python
# Basic types
"~ task"                              # Simple task
"* event"                             # Simple event
"% note"                              # Simple note
"! goal"                              # Simple goal

# With dates
"~ task @s 2025-01-15"                # Task with date
"* event @s 2025-01-15 10:00"         # Event with datetime
"* event @s 2025-01-15 10:00 @e 1h"   # Event with extent

# With priority
"~ task @p 1"                         # Priority 1 (highest)
"~ task @s 2025-01-15 @p 2"           # Date and priority

# With description
"~ task @d This is a description"     # With description
"~ task @s 2025-01-15 @p 1 @d Desc"   # Multiple attributes

# With bins
"~ task @b work/projects"             # Single bin
"~ task @b work/projects @b urgent/tags"  # Multiple bins

# Repeating
"~ task @s 2025-01-15 @r d"           # Daily
"~ task @s 2025-01-15 @r w"           # Weekly
"~ task @s 2025-01-15 @r d &c 5"      # Daily, 5 times

# Complex
"* meeting @s 2025-01-15 14:00 @e 1h @r w @p 1 @d Weekly standup"
```

## Running Tests

```bash
# All tests
uv run pytest

# Specific file
uv run pytest tests/test_item_parsing.py

# Specific test
uv run pytest tests/test_item_parsing.py::test_simple_task

# By marker
uv run pytest -m unit              # Unit tests only
uv run pytest -m integration       # Integration tests only

# With output
uv run pytest -v                   # Verbose
uv run pytest -s                   # Show print statements
uv run pytest -x                   # Stop at first failure

# Coverage
uv run pytest --cov=src/tklr
uv run pytest --cov=src/tklr --cov-report=html

# By name pattern
uv run pytest -k "priority"        # Tests matching "priority"
uv run pytest -k "not slow"        # Skip slow tests
```

## Debugging Tests

```python
# Add print statements (run with -s)
def test_debug(item_factory):
    item = item_factory("~ task")
    print(f"Item: {item.__dict__}")  # Print all attributes
    assert item.parse_ok

# Use debugger (run with --pdb)
def test_with_debugger(item_factory):
    item = item_factory("~ task")
    breakpoint()  # Drops into debugger
    assert item.parse_ok

# Show local variables on failure (run with -l)
def test_show_locals(item_factory):
    item = item_factory("~ task")
    result = item.some_method()
    assert result == "expected"  # Failure shows local vars
```

## Common Patterns

### Test Parse Success
```python
def test_parse_success(item_factory):
    item = item_factory("~ task @s 2025-01-15")
    assert item.parse_ok, f"Parse failed: {item.parse_message}"
```

### Test Parse Failure
```python
def test_parse_failure(item_factory):
    item = item_factory("~ invalid syntax ???")
    assert not item.parse_ok
    assert len(item.parse_message) > 0
```

### Test Multiple Items
```python
def test_multiple_items(test_controller, item_factory):
    entries = [
        "~ task one",
        "~ task two",
        "* event one",
    ]

    for entry in entries:
        item = item_factory(entry)
        if item.parse_ok:
            test_controller.add_item(item)
```

### Test Time-Dependent Behavior
```python
def test_overdue(item_factory):
    with freeze_time("2025-01-20 12:00:00"):
        # Create item scheduled for the past
        item = item_factory("~ task @s 2025-01-15")

        assert item.parse_ok
        # Test overdue detection
```

### Regression Test
```python
def test_bug_123_description():
    """
    Regression test for GitHub issue #123.

    Bug: Items with very long descriptions were truncated.
    Fixed: Now handles descriptions up to 10,000 characters.
    """
    long_desc = "x" * 10000
    item = item_factory(f"~ task @d {long_desc}")

    assert item.parse_ok
    assert len(item.description) == 10000
```

## Tips

1. **Always check parse_ok first**
   ```python
   assert item.parse_ok, f"Parse failed: {item.parse_message}"
   ```

2. **Use descriptive test names**
   ```python
   # Good
   def test_repeating_task_with_count_limit():

   # Bad
   def test_repeat():
   ```

3. **One concept per test**
   ```python
   # Test one thing well
   def test_priority_parsing(item_factory):
       item = item_factory("~ task @p 1")
       assert item.priority == 1
   ```

4. **Use fixtures for setup**
   ```python
   # Don't repeat yourself
   def test_with_fixture(item_factory):
       item = item_factory("~ task")
       # item_factory handles env, controller, etc.
   ```

5. **Write tests as you code**
   - Fix a bug? Add a regression test.
   - Add a feature? Add a feature test.
   - Tests document your code!
