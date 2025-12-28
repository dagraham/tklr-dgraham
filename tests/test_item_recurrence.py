"""
Tests for repeating/recurring items.

These tests verify rrule parsing, repeat patterns, and related functionality.
"""

import pytest
from datetime import datetime, timedelta
from tklr.item import Item


@pytest.mark.unit
class TestBasicRecurrence:
    """Test basic recurring patterns."""

    def test_daily_repeat(self, frozen_time, item_factory):
        """Test daily recurrence pattern."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ daily task @s 2025-01-15 10:00 @r d")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have daily rrule

    def test_weekly_repeat(self, frozen_time, item_factory):
        """Test weekly recurrence pattern."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* weekly meeting @s 2025-01-15 14:00 @e 1h @r w")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have weekly rrule

    def test_monthly_repeat(self, frozen_time, item_factory):
        """Test monthly recurrence pattern."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ monthly reminder @s 2025-01-15 @r m")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have monthly rrule


@pytest.mark.unit
class TestRecurrenceWithInterval:
    """Test recurring patterns with custom intervals."""

    def test_every_other_day(self, frozen_time, item_factory):
        """Test recurrence every 2 days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ every other day @s 2025-01-15 @r d &i 2")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_every_third_day(self, frozen_time, item_factory):
        """Test recurrence every 3 days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ every third day @s 2025-01-15 @r d &i 3")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_every_two_weeks(self, frozen_time, item_factory):
        """Test recurrence every 2 weeks."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ biweekly task @s 2025-01-15 @r w &i 2")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
@pytest.mark.unit
class TestRecurrenceWithCount:
    """Test recurring patterns with count limits."""

    def test_repeat_with_count(self, frozen_time, item_factory):
        """Test recurrence with specific count."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ repeat 3 times @s 2025-01-15 @r d &c 3")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should repeat exactly 3 times

    def test_all_day_repeat_with_count(self, frozen_time, item_factory):
        """Test all-day recurrence with count."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* all-day every Tuesday @s 2025-01-20 @r w &c 3")

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_event_repeat_with_count(self, frozen_time, item_factory):
        """Test event recurrence with count and extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event 5 times @s 2025-01-22 9a @e 2h @r d &i 3 &c 5"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
@pytest.mark.unit
class TestRecurrenceWithUntil:
    """Test recurring patterns with end dates."""

    def test_repeat_until_date(self, frozen_time, item_factory):
        """Test recurrence with until date."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* repeating until @s 2025-01-15 7:30p @e 1h @r d &u 2025-01-29"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should repeat until 2025-01-29


@pytest.mark.unit
class TestRecurrenceByWeekday:
    """Test recurring patterns on specific weekdays."""

    def test_weekly_specific_days(self, frozen_time, item_factory):
        """Test recurrence on specific weekdays (Mon, Wed, Fri)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* MWF pattern @s 2025-01-15 @r w &w MO,WE,FR &c 10"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should repeat on Mon, Wed, Fri only

    def test_monthly_third_thursday(self, frozen_time, item_factory):
        """Test monthly recurrence on specific weekday (3rd Thursday)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* Tiki Roundtable @s 2025-01-01 14:00 z UTC @e 1h30m @r m &w +3TH &c 10"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should repeat on 3rd Thursday of each month


@pytest.mark.unit
class TestRecurrenceWithRdates:
    """Test recurring items with additional specific dates (rdates)."""

    def test_repeating_with_rdates(self, frozen_time, item_factory):
        """Test daily recurrence plus specific additional dates."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ repeating and rdates @s 2025-01-15 1:30p @r d @+ 2:30p, 3:30p"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have both rrule and rdates

    def test_repeating_rdates_and_finish(self, frozen_time, item_factory):
        """Test recurrence with rdates and finish time."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ complex repeat @s 2025-01-15 1:30p @r d &c 3 @+ 10:30a, 3:30p @f 8:15a"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_multiple_datetimes_over_weeks(self, frozen_time, item_factory):
        """Test specific datetimes across multiple weeks."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* weekly meetings @s 2025-01-08 4p @e 1h @+ 2025-01-15 4p, 2025-01-22 4p"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
@pytest.mark.unit
class TestComplexRecurrence:
    """Test complex recurring patterns."""

    def test_daily_with_extent_and_count(self, frozen_time, item_factory):
        """Test daily events with duration and count."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event series @s 2025-01-22 8:30a @e 4h @r d &c 3"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_daily_with_interval_and_count(self, frozen_time, item_factory):
        """Test every Nth day with count limit."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* every 3rd day @s 2025-01-15 @r d &i 3 &c 10"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_daily_datetime_with_extent(self, frozen_time, item_factory):
        """Test daily datetime with extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* daily meeting @s 2025-01-15 3p @e 30m @r d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
    def test_daily_at_specific_time(self, frozen_time, item_factory):
        """Test daily task at specific time."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ daily at 10am @s 2025-01-15 10:00 @r d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
