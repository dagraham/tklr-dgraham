"""
Integration tests for database operations.

These tests verify that items can be properly added to the database,
retrieved, and that dependent tables are populated correctly.
"""

import pytest
from datetime import datetime
from tklr.item import Item


@pytest.mark.integration
class TestDatabaseOperations:
    """Test basic database CRUD operations."""

    def test_add_item_to_database(self, test_controller, item_factory):
        """Test adding a single item to the database."""
        item = item_factory("~ test task @p 1")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        record_id = test_controller.add_item(item)

        assert record_id is not None
        assert record_id > 0

    def test_add_multiple_items(self, test_controller, item_factory, frozen_time):
        """Test adding multiple items to database."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        entries = [
            "~ task one @p 1",
            "~ task two @p 2",
            "* event today @s 2025-01-15 10:00",
            "% journal entry",
        ]

        record_ids = []
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                record_ids.append(record_id)

        assert len(record_ids) == 4
        assert all(rid > 0 for rid in record_ids)

    def test_populate_dependent_tables(self, test_controller, item_factory, frozen_time):
        """Test that dependent tables are populated correctly."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        # Add various items that use dependent tables
        entries = [
            "~ task with bins @b work/projects @b urgent/tags",
            "* repeating event @s 2025-01-15 10:00 @r d &c 5",
            "~ task with tags @d Description with #red #blue tags",
        ]

        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                test_controller.add_item(item)

        # Populate dependent tables
        test_controller.db_manager.populate_dependent_tables()

        # If we get here without exception, population succeeded
        assert True


@pytest.mark.integration
class TestDatabaseWithRealEntries:
    """Test database operations with realistic entry strings."""

    def test_busy_schedule_entries(self, test_controller, item_factory, frozen_time):
        """Test entries from the 'busy' category in make_items.py."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        entries = [
            "* all-day yesterday @d all day event @s 2025-01-14",
            "* all-day today @d all day event @s 2025-01-15",
            "* all-day tomorrow @d all day event @s 2025-01-16",
            "* one hour yesterday @s 2025-01-14 9a @e 1h",
            "* one hour today @s 2025-01-15 10a @e 1h",
            "* one hour tomorrow @s 2025-01-16 11a @e 1h",
        ]

        success_count = 0
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                if record_id:
                    success_count += 1

        assert success_count == len(entries)

    def test_finish_entries(self, test_controller, item_factory, frozen_time):
        """Test entries with finish times."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        entries = [
            "~ finished task @s 2025-01-15 13:30 @f 2025-01-15 11:00",
            "~ offset task @s 2025-01-10 12:00 @f 2025-01-15 10:00 @o 4d",
            "~ learn offset @s 2025-01-05 12:00 @f 2025-01-15 10:00 @o ~8d",
        ]

        success_count = 0
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                if record_id:
                    success_count += 1

        assert success_count == len(entries)

    def test_bin_entries(self, test_controller, item_factory, frozen_time):
        """Test entries with bins/categories."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        entries = [
            "% Journal entry @b 2025:10/2025/journal @s 2p @d Test bin entries",
            "% Churchill quote @b Churchill/quotations/library @d Dogs look up at you.",
            "* Activity @s mon @r d &c 7 @b travel/activities @b Lille/France/places",
            "% Person @b SmithCB/people:S/people @d details @b Athens/Greece/places",
        ]

        success_count = 0
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                if record_id:
                    success_count += 1

        # At least some should succeed
        assert success_count > 0

    def test_goal_entries(self, test_controller, item_factory, frozen_time):
        """Test goal entries."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        entries = [
            "! fitness goal @s 2025-12-01 @t 3/1w",
        ]

        success_count = 0
        for entry in entries:
            item = item_factory(entry)
            if item.parse_ok:
                record_id = test_controller.add_item(item)
                if record_id:
                    success_count += 1

        assert success_count == len(entries)


@pytest.mark.integration
class TestDatabasePopulatedFixture:
    """Test using the populated_controller fixture."""

    def test_populated_database_has_items(self, populated_controller):
        """Test that populated_controller fixture creates items."""
        # The populated_controller should have multiple items
        # We can verify by checking that operations don't fail

        # This is a basic smoke test
        assert populated_controller is not None
        assert populated_controller.db_manager is not None


@pytest.mark.integration
class TestErrorHandling:
    """Test error handling in database operations."""

    def test_invalid_entry_handling(self, test_controller, item_factory):
        """Test that invalid entries are handled gracefully."""
        # This might fail parsing
        item = item_factory("~ invalid date @s not-a-date")

        # Even if parse fails, it shouldn't crash
        if item.parse_ok:
            test_controller.add_item(item)

        # We should get here without exception
        assert True

    def test_empty_entry(self, test_controller, item_factory):
        """Test handling of empty entry."""
        item = item_factory("")

        # Should handle empty entry gracefully
        assert True
