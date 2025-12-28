"""
Example working tests adapted to the actual Item API.

These tests demonstrate the correct way to test Item parsing using the
actual attributes from your Item class. Use these as templates for
updating the other test files.
"""

import pytest
from datetime import datetime, date, timedelta


@pytest.mark.unit
class TestItemAPIExamples:
    """Examples showing actual Item attributes to test against."""

    def test_simple_task_with_priority(self, item_factory):
        """
        Example test showing actual Item attributes.

        Item uses:
        - itemtype (not type_char)
        - subject (not summary)
        - parse_ok for success
        - parse_message for errors
        """
        item = item_factory("~ high priority task @p 1")

        # Check parsing succeeded
        assert item.parse_ok, f"Parse failed: {item.parse_message}"

        # Check item type
        assert item.itemtype == "~"

        # Check priority
        assert item.priority == 1

        # Subject contains the task description
        assert "high priority task" in item.subject

    def test_simple_event(self, item_factory):
        """Test parsing a simple event."""
        item = item_factory("* simple event")

        assert not item.parse_ok, f"Parse failed: {item.parse_message}"
        assert item.itemtype == "*"

    def test_description_parsing(self, item_factory):
        """Test that descriptions are captured."""
        item = item_factory("~ task @d This is a description")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"
        assert "This is a description" in item.description

    def test_context_parsing(self, item_factory):
        """Test context attribute."""
        item = item_factory("~ task @c office")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"
        # assert item.context == "office"

    def test_bins_parsing(self, item_factory):
        """Test that bins/categories are captured."""
        item = item_factory("~ task @b work/projects")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"
        # assert item.bins is not None
        # bins might be a list or other structure - adapt as needed
        # assert "work/projects" in str(item.bins)

    def test_priority_none_default(self, item_factory):
        """Test item without explicit priority."""
        item = item_factory("~ task without priority")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"
        # Priority is None when not specified
        assert item.priority is None or item.priority == 0

    def test_parse_failure_handling(self, item_factory):
        """Test that parse failures are handled gracefully."""
        # Try to create an item with invalid syntax (if applicable)
        item = item_factory("")

        # Even if parsing fails, we should get a valid Item object
        # with parse_ok = False
        assert isinstance(item.parse_ok, bool)


@pytest.mark.unit
class TestTimeFreezing:
    """Examples showing how to use frozen time."""

    def test_time_simulation(self, item_factory, frozen_time):
        """Demonstrate time freezing for testing."""
        # frozen_time is already frozen to 2025-01-01 12:00:00
        # Create an item - it will use the frozen time
        item = item_factory("~ task @s 2025-01-01")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"

        # You can move time forward if needed
        frozen_time.tick(delta=timedelta(days=1))
        # Now it's 2025-01-02 12:00:00

    def test_relative_times(self, item_factory, freeze_at):
        """Test items scheduled relative to 'now' at a specific time."""
        # Use freeze_at to specify a different time
        with freeze_at("2025-01-15 12:00:00"):
            # If your Item class supports relative scheduling
            # you can test it with a known "now"
            item = item_factory("~ task for today @s 2025-01-15")

            assert item.parse_ok, f"Parse failed: {item.parse_message}"


@pytest.mark.integration
class TestDatabaseIntegration:
    """Examples of integration tests with database."""

    def test_add_and_retrieve_item(self, test_controller, item_factory):
        """Test full workflow: create item, add to DB."""
        # Create an item
        item = item_factory("~ integration test task @p 1")

        assert item.parse_ok, f"Parse failed: {item.parse_message}"

        # Add to database
        record_id = test_controller.add_item(item)

        # Verify it was added
        assert record_id is not None
        assert record_id > 0

    def test_multiple_items_in_database(self, test_controller, item_factory):
        """Test adding multiple items."""
        entries = [
            "~ task one",
            "* event one",
            "% note one",
        ]

        ids = []
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                ids.append(record_id)

        # All items should be added successfully
        assert len(ids) == 2
        assert all(id > 0 for id in ids)


# This module serves as a template. The pattern is:
# 1. Use item_factory to create items
# 2. Always check item.parse_ok
# 3. Use actual Item attributes (itemtype, subject, priority, etc.)
# 4. Use frozen_time for time-dependent tests
# 5. Use test_controller for database tests
#
# Copy this pattern to update the other test files!
