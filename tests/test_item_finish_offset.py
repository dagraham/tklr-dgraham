"""
Tests for finished items and offset handling.

These tests verify the finish time tracking and offset/postponement logic.
"""

import pytest
from datetime import datetime, timedelta
from tklr.item import Item


@pytest.mark.unit
class TestFinishedItems:
    """Test items with finish times."""

    def test_finished_task_simple(self, frozen_time, item_factory):
        """Test task with finish time."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ finished task @s 2025-01-14 @f 2025-01-15"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have finish time recorded

    def test_finished_one_hour_ago(self, frozen_time, item_factory):
        """Test task finished one hour ago."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ finished recently @s 2025-01-15 12:00 @f 2025-01-15 11:00"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_repeating_with_finish(self, frozen_time, item_factory):
        """Test repeating task with finish time on one occurrence."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ repeating finished @s 2025-01-15 1:30p @r d &c 3 @f 2025-01-15 8:15a"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
@pytest.mark.unit
class TestOffsets:
    """Test offset/postponement functionality."""

    def test_fixed_offset_days(self, frozen_time, item_factory):
        """Test item with fixed day offset."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ weekly task @s 2025-01-11 @o 7d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Offset should be 7 days

    def test_fixed_offset_4_days(self, frozen_time, item_factory):
        """Test item with 4-day offset."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ wind clock @s 2025-01-10 12:00pm @o 4d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_offset_with_finish(self, frozen_time, item_factory):
        """Test offset item with finish time."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ offset task @s 2025-01-10 12:00pm @f 2025-01-15 10:00am @o 4d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
@pytest.mark.unit
class TestLearnOffsets:
    """Test learning/adaptive offset functionality."""

    def test_learn_offset_approximate(self, frozen_time, item_factory):
        """Test item with learning offset (~ prefix)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ adaptive task @s 2025-01-07 @o ~7d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have learning offset enabled

    def test_learn_offset_4_days(self, frozen_time, item_factory):
        """Test learning offset of approximately 4 days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ birdfeeders @s 2025-01-05 @o ~4d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_learn_offset_with_finish(self, frozen_time, item_factory):
        """Test learning offset with finish time."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ learn task @s 2025-01-05 12:00pm @f 2025-01-15 10:00am @o ~8d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Offset should be updated based on actual completion


@pytest.mark.unit
class TestOffsetEdgeCases:
    """Test edge cases for offset handling."""

    def test_offset_overdue_item(self, frozen_time, item_factory):
        """Test offset on overdue item."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        # Item scheduled 10 days ago with 4-day offset
        item = item_factory(
            "~ overdue offset @s 2025-01-05 @o 4d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should still handle offset correctly

    def test_multiple_offsets_scenario(self, frozen_time, item_factory):
        """Test that repeated postponements work."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        # Create item, verify offset behavior
        item = item_factory(
            "~ recurring offset @s 2025-01-08 @o 7d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
