# How to Use Test Fixtures Correctly

## Time Freezing with freezegun

### The `frozen_time` Fixture

**Use this when:** You need time frozen to the default test time (2025-01-01 12:00:00)

```python
def test_with_default_frozen_time(item_factory, frozen_time):
    """Time is already frozen to 2025-01-01 12:00:00"""
    # No need to call freeze() - it's already frozen!

    item = item_factory("~ task @s 2025-01-01")
    assert item.parse_ok

    # Move time forward if needed
    frozen_time.tick(delta=timedelta(hours=2))
    # Now it's 2025-01-01 14:00:00
```

### The `freeze_at` Fixture

**Use this when:** You need to freeze time to a specific datetime

```python
def test_at_specific_time(item_factory, freeze_at):
    """Freeze to a custom datetime"""

    with freeze_at("2025-01-15 10:00:00"):
        # Time is frozen to Jan 15, 2025 at 10am
        item = item_factory("~ task @s 2025-01-15")
        assert item.parse_ok
```

### The `mock_now` Fixture

**Use this when:** You just need a fixed "now" value

```python
def test_with_mock_now(item_factory, mock_now):
    """mock_now is just datetime(2025, 1, 1, 12, 0, 0)"""

    # Time is frozen via the frozen_time fixture
    # mock_now just gives you the datetime object
    assert mock_now == datetime(2025, 1, 1, 12, 0, 0)
```

## ❌ INCORRECT Patterns (Don't Use These)

```python
# ❌ WRONG - frozen_time doesn't have a freeze() method
def test_wrong(frozen_time):
    frozen_time.freeze("2025-01-15 10:00:00")  # AttributeError!
```

```python
# ❌ WRONG - need to use context manager
def test_wrong(freeze_at):
    freeze_at("2025-01-15 10:00:00")  # Missing 'with' statement!
```

## ✅ CORRECT Patterns

```python
# ✅ Use frozen_time for default time
def test_correct(frozen_time, item_factory):
    # Already frozen to 2025-01-01 12:00:00
    item = item_factory("~ task @s 2025-01-01")
    assert item.parse_ok

# ✅ Use freeze_at for custom time
def test_correct(freeze_at, item_factory):
    with freeze_at("2025-01-15 10:00:00"):
        item = item_factory("~ task @s 2025-01-15")
        assert item.parse_ok

# ✅ Move time forward
def test_correct(frozen_time, item_factory):
    # Start at 2025-01-01 12:00:00
    item1 = item_factory("~ task @s 2025-01-01")

    # Move forward 1 day
    frozen_time.tick(delta=timedelta(days=1))

    # Now it's 2025-01-02 12:00:00
    item2 = item_factory("~ task @s 2025-01-02")

# ✅ Use context fixtures
def test_with_context(overdue_context, item_factory):
    # Time is frozen to 2025-01-15 12:00:00
    # overdue_context provides helpful date strings
    item = item_factory(f"~ task @s {overdue_context['yesterday']}")
    assert item.parse_ok
```

## Context Fixtures

### `overdue_context`

Sets time to 2025-01-15 12:00:00 with helpful date references:

```python
def test_overdue(overdue_context, item_factory):
    # Time is frozen to 2025-01-15 12:00:00
    # overdue_context = {
    #     "now": datetime(2025, 1, 15, 12, 0, 0),
    #     "yesterday": "2025-01-14",
    #     "today": "2025-01-15",
    #     "tomorrow": "2025-01-16",
    # }

    item = item_factory(f"~ task @s {overdue_context['yesterday']}")
    # Test overdue behavior
```

### `future_context`

Sets time to 2025-01-01 09:00:00 for testing upcoming items:

```python
def test_upcoming(future_context, item_factory):
    # Time is frozen to 2025-01-01 09:00:00
    # future_context = {
    #     "now": datetime(2025, 1, 1, 9, 0, 0),
    #     "in_one_hour": "2025-01-01 10:00",
    #     "in_one_day": "2025-01-02 09:00",
    #     "in_one_week": "2025-01-08 09:00",
    # }

    item = item_factory(f"~ task @s {future_context['in_one_hour']}")
    # Test upcoming item behavior
```

## Database Fixtures

### `test_controller`

Fresh database for each test:

```python
def test_database(test_controller, item_factory):
    item = item_factory("~ task @s 2025-01-15")

    record_id = test_controller.add_item(item)
    assert record_id > 0
```

### `populated_controller`

Database pre-loaded with sample items:

```python
def test_with_data(populated_controller):
    # Database already has sample items loaded
    # Use for testing queries, aggregations, etc.
```

## Item Creation

### `item_factory`

Easy item creation:

```python
def test_factory(item_factory):
    # Creates Item with proper env, controller, etc.
    item = item_factory("~ task @s 2025-01-15 @p 1")

    assert item.parse_ok
    assert item.priority == 1
```

### `sample_items`

Pre-defined test cases:

```python
def test_samples(sample_items, item_factory):
    # sample_items is a dict of common test entry strings
    task = item_factory(sample_items['simple_task'])
    event = item_factory(sample_items['event_with_time'])
```

## Quick Reference

| Fixture | Use When | Example |
|---------|----------|---------|
| `frozen_time` | Need default time (2025-01-01 12:00) | `def test(frozen_time):` |
| `freeze_at` | Need specific time | `with freeze_at("2025-01-15 10:00"):` |
| `mock_now` | Just need datetime object | `assert now == mock_now` |
| `overdue_context` | Testing overdue items | `def test(overdue_context):` |
| `future_context` | Testing upcoming items | `def test(future_context):` |
| `item_factory` | Creating items | `item = item_factory("~ task")` |
| `test_controller` | Fresh database | `def test(test_controller):` |
| `populated_controller` | Database with data | `def test(populated_controller):` |

## Common Mistakes and Fixes

### Mistake 1: Calling freeze() on frozen_time

```python
# ❌ WRONG
def test_wrong(frozen_time):
    frozen_time.freeze("2025-01-15")  # AttributeError!

# ✅ CORRECT - use freeze_at instead
def test_correct(freeze_at):
    with freeze_at("2025-01-15 12:00:00"):
        # ...
```

### Mistake 2: Not using context manager with freeze_at

```python
# ❌ WRONG
def test_wrong(freeze_at):
    freeze_at("2025-01-15")  # Missing 'with'!

# ✅ CORRECT
def test_correct(freeze_at):
    with freeze_at("2025-01-15 12:00:00"):
        # ...
```

### Mistake 3: Forgetting frozen_time is already frozen

```python
# ⚠️ UNNECESSARY
def test_redundant(frozen_time, freeze_at):
    with freeze_at("2025-01-01 12:00:00"):  # Already frozen to this!
        # ...

# ✅ BETTER
def test_better(frozen_time):
    # Already frozen to 2025-01-01 12:00:00
    # ...
```
