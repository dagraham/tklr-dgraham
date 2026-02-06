"""
Shared pytest fixtures for tklr tests.

This module provides common fixtures used across all test files, including:
- Time freezing utilities
- Test environment setup
- Database fixtures
- Test data factories
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta
from freezegun import freeze_time

from tklr.tklr_env import TklrEnvironment
from tklr.controller import Controller
from tklr.item import Item


@pytest.fixture
def frozen_time():
    """
    Provides a freezegun context that freezes time to a default datetime.

    Time is automatically frozen to 2025-01-01 12:00:00 for the duration of the test.
    You can move time forward using the methods on the frozen context.

    Usage:
        def test_something(frozen_time):
            # Time is already frozen to 2025-01-01 12:00:00
            now = datetime.now()  # Returns 2025-01-01 12:00:00

            # Move time forward
            frozen_time.tick(delta=timedelta(hours=2))
            now = datetime.now()  # Returns 2025-01-01 14:00:00
    """
    with freeze_time("2025-01-01 12:00:00") as frozen:
        yield frozen


@pytest.fixture
def freeze_at():
    """
    Returns a function that freezes time to a specific datetime.

    Usage:
        def test_something(freeze_at):
            with freeze_at("2025-01-15 10:00:00"):
                # Time is frozen to this specific moment
                now = datetime.now()
    """
    return freeze_time


@pytest.fixture
def test_env():
    """
    Provides a TklrEnvironment configured for testing.
    """
    env = TklrEnvironment()
    return env


@pytest.fixture
def temp_db_path(tmp_path):
    """
    Provides a temporary database path that will be cleaned up after the test.
    """
    db_path = tmp_path / "test_tklr.db"
    yield db_path
    # Cleanup happens automatically with tmp_path


@pytest.fixture
def test_controller(temp_db_path, test_env):
    """
    Provides a Controller with a fresh test database.

    The database is automatically cleaned up after each test.
    """
    ctrl = Controller(str(temp_db_path), test_env, reset=True)
    yield ctrl
    # Close database connection to avoid ResourceWarning
    try:
        if hasattr(ctrl, 'db_manager') and hasattr(ctrl.db_manager, 'conn'):
            ctrl.db_manager.conn.close()
    except Exception:
        pass  # Ignore errors during cleanup


@pytest.fixture
def sample_items():
    """
    Provides a dictionary of sample entry strings for common test scenarios.

    Returns:
        dict: Keys are descriptive names, values are entry strings
    """
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    tomorrow = (now + timedelta(days=1)).strftime("%Y-%m-%d")
    yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

    return {
        # Basic items
        "simple_task": "~ simple task",
        "simple_event": "* simple event",
        "simple_journal": "% simple journal entry",

        # Tasks with dates
        "task_today": f"~ task today @s {today}",
        "task_tomorrow": f"~ task tomorrow @s {tomorrow}",
        "task_yesterday": f"~ task yesterday @s {yesterday}",

        # Tasks with priorities
        "task_priority_1": "~ high priority task @p 1",
        "task_priority_2": "~ medium priority task @p 2",
        "task_priority_3": "~ low priority task @p 3",

        # Events with times
        "event_with_time": f"* meeting @s {today} 10:00 @e 1h",
        "event_all_day": f"* all day event @s {today}",

        # Repeating items
        "daily_task": f"~ daily task @s {today} @r d",
        "weekly_event": f"* weekly meeting @s {today} 14:00 @e 1h @r w",
        "monthly_reminder": f"~ monthly reminder @s {today} @r m",

        # Timezones
        "naive_time": f"* noon meeting @s {today} 12:00 z none",
        "utc_time": f"* utc meeting @s {today} 12:00 z UTC",
        "pacific_time": f"* pacific meeting @s {today} 12:00 z US/Pacific",

        # Complex items
        "task_with_description": f"~ task with details @s {today} @d This is a detailed description #tag",
        "task_with_bins": f"~ categorized task @b work/projects @b urgent/tags",

        # Finished items
        "finished_task": f"~ finished task @s {yesterday} @f {today}",

        # Items with offsets
        "task_with_offset": f"~ weekly task @s {yesterday} @o 7d",
        "task_with_learn_offset": f"~ adaptive task @s {yesterday} @o ~7d",

        # Goals
        "simple_goal": f"! fitness goal @s {today} @t 3/1w",
    }


@pytest.fixture
def item_factory(test_env, test_controller):
    """
    Provides a factory function for creating Item instances.

    Usage:
        def test_something(item_factory):
            item = item_factory("~ task @s 2025-01-01")
            assert item.parse_ok
    """
    def _create_item(entry_str: str, final: bool = True) -> Item:
        return Item(raw=entry_str, env=test_env, final=final, controller=test_controller)

    return _create_item


@pytest.fixture
def use_factory(test_controller):
    """
    Helper fixture to create uses for tests that rely on @u lookup.
    """
    def _create(name: str = "General", details: str = ""):
        return test_controller.db_manager.add_use(name, details)

    return _create


@pytest.fixture
def populated_controller(test_controller, item_factory, sample_items):
    """
    Provides a Controller with a database populated with sample items.

    This is useful for integration tests that need a realistic database state.
    """
    # Add all sample items to the database
    for name, entry in sample_items.items():
        item = item_factory(entry)
        if item.parse_ok:
            test_controller.add_item(item)

    # Populate dependent tables
    test_controller.db_manager.populate_dependent_tables()

    return test_controller


# Utility fixtures for common test scenarios

@pytest.fixture
def mock_now(frozen_time):
    """
    Freezes time to a standard test datetime (2025-01-01 12:00:00).

    This is simpler than frozen_time for tests that just need a fixed "now".
    The frozen_time fixture already freezes to this time, so we just return it.
    """
    return datetime(2025, 1, 1, 12, 0, 0)


@pytest.fixture
def overdue_context(freeze_at):
    """
    Sets up a time context where items from yesterday are overdue.
    """
    with freeze_at("2025-01-15 12:00:00"):
        yield {
            "now": datetime(2025, 1, 15, 12, 0, 0),
            "yesterday": "2025-01-14",
            "today": "2025-01-15",
            "tomorrow": "2025-01-16",
        }


@pytest.fixture
def future_context(freeze_at):
    """
    Sets up a time context for testing upcoming items.
    """
    with freeze_at("2025-01-01 09:00:00"):
        yield {
            "now": datetime(2025, 1, 1, 9, 0, 0),
            "in_one_hour": "2025-01-01 10:00",
            "in_one_day": "2025-01-02 09:00",
            "in_one_week": "2025-01-08 09:00",
        }


# Helper functions

def bin_path_contains_prefix(bin_paths, prefix):
    """
    Check if any bin path starts with the given prefix.

    Bin paths in tklr are hierarchical lists like ["Churchill", "quotations", "library"].
    This helper checks if a prefix matches the beginning of any complete bin path.

    Args:
        bin_paths: List of bin path lists, e.g., [["Churchill", "quotations", "library"]]
        prefix: List representing a bin prefix, e.g., ["Churchill"] or ["Churchill", "quotations"]

    Returns:
        True if any bin path starts with prefix, False otherwise

    Examples:
        >>> bin_paths = [["Churchill", "quotations", "library"]]
        >>> bin_path_contains_prefix(bin_paths, ["Churchill"])  # True
        >>> bin_path_contains_prefix(bin_paths, ["Churchill", "quotations"])  # True
        >>> bin_path_contains_prefix(bin_paths, ["Churchill", "quotations", "library"])  # True
        >>> bin_path_contains_prefix(bin_paths, ["Churchill", "library"])  # False (not a valid prefix)
        >>> bin_path_contains_prefix(bin_paths, ["Shakespeare"])  # False (wrong prefix)

    Note:
        A valid prefix must match the start of a bin path exactly - you cannot skip
        intermediate components. ["Churchill", "library"] is not a valid prefix of
        ["Churchill", "quotations", "library"] because it skips "quotations".
    """
    prefix_tuple = tuple(prefix)
    return any(
        tuple(path[:len(prefix_tuple)]) == prefix_tuple
        for path in bin_paths
    )
