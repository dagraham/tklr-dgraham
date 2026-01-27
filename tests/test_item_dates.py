"""
Tests for Item date and time parsing.

These tests verify date/datetime parsing, timezone handling, and
temporal operations like overdue detection.
"""

import pytest
from datetime import datetime, date, timedelta
from tklr.item import Item


@pytest.mark.unit
class TestDateParsing:
    """Test basic date parsing."""

    def test_date_only(self, frozen_time, item_factory):
        """Test parsing item with date only (no time)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task @s 2025-01-15")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should parse as date or datetime at start of day

    def test_date_today(self, frozen_time, item_factory):
        """Test parsing item scheduled for today."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task today @s 2025-01-15")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_date_yesterday(self, frozen_time, item_factory):
        """Test parsing item from yesterday."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task yesterday @s 2025-01-14")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_date_tomorrow(self, frozen_time, item_factory):
        """Test parsing item for tomorrow."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task tomorrow @s 2025-01-16")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_first_of_month(self, frozen_time, item_factory):
        """Test parsing item scheduled for first of month."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* first of the month @s 2025-01-01")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"


@pytest.mark.unit
class TestDatetimeParsing:
    """Test datetime (date + time) parsing."""

    def test_datetime_with_time(self, frozen_time, item_factory):
        """Test parsing datetime with hour and minute."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* meeting @s 2025-01-15 10:00")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should have time component

    def test_datetime_with_am_pm(self, frozen_time, item_factory):
        """Test parsing datetime with AM/PM notation."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* morning meeting @s 2025-01-15 9a")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        item = item_factory("* afternoon meeting @s 2025-01-15 2p")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_datetime_with_minutes(self, frozen_time, item_factory):
        """Test parsing datetime with specific minutes."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task @s 2025-01-15 1:30p")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_all_day_event(self, frozen_time, item_factory):
        """Test parsing all-day event."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* all-day event @s 2025-01-15 @d all day event")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"


@pytest.mark.unit
class TestTimezones:
    """Test timezone handling."""

    def test_naive_timezone(self, frozen_time, item_factory):
        """Test parsing with naive timezone (z none)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* noon meeting @s 2025-01-15 12:00 z none")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should be timezone-naive

    def test_utc_timezone(self, frozen_time, item_factory):
        """Test parsing with UTC timezone."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* utc meeting @s 2025-01-15 12:00 z UTC")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should be timezone-aware (UTC)

    def test_pacific_timezone(self, frozen_time, item_factory):
        """Test parsing with US/Pacific timezone."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* pacific meeting @s 2025-01-15 3:00p z US/Pacific")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should be timezone-aware (Pacific)

    def test_cet_timezone(self, frozen_time, item_factory):
        """Test parsing with CET timezone."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* timezone test @s 2025-01-15 12p z CET")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_timezone_from_z_shorthand(self, frozen_time, item_factory):
        """Test 'from z' shorthand for timezone."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* event @s 2025-01-15 10h z none")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"


@pytest.mark.unit
class TestExtentDuration:
    """Test event extent/duration parsing."""

    def test_extent_hours(self, frozen_time, item_factory):
        """Test parsing event with hour extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* meeting @s 2025-01-15 10:00 @e 1h")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should have 1 hour extent

    def test_extent_minutes(self, frozen_time, item_factory):
        """Test parsing event with minute extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* short meeting @s 2025-01-15 10:00 @e 30m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_extent_hours_minutes(self, frozen_time, item_factory):
        """Test parsing event with hours and minutes."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* long meeting @s 2025-01-15 10:00 @e 1h30m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_extent_days(self, frozen_time, item_factory):
        """Test parsing event spanning multiple days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* conference @s 2025-01-15 9:00 @e 2d")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_extent_complex(self, frozen_time, item_factory):
        """Test parsing event with complex extent (days, hours, minutes)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* spanning event @s 2025-01-15 19:00 @e 2d2h30m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_zero_extent(self, frozen_time, item_factory):
        """Test parsing event with zero extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("* zero extent @s 2025-01-16 10:00 z none")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"


@pytest.mark.unit
class TestMultipleDatetimes:
    """Test items with multiple datetime occurrences."""

    def test_two_datetimes(self, frozen_time, item_factory):
        """Test parsing item with two datetimes (rdates)."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task @s 9am @+ 10am")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should have multiple datetime occurrences

    def test_three_datetimes(self, frozen_time, item_factory):
        """Test parsing item with three specific datetimes."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("~ task @s 9am @+ 10am, 11am")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_three_datetimes_with_extent(self, frozen_time, item_factory):
        """Test event with multiple datetimes and extent."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* meetings @s 2025-01-15 10:00 @e 45m @+ 2025-01-15 14:00, 2025-01-16 09:00"
        )

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"


@pytest.mark.unit
class TestRelativeTimes:
    """Test relative time expressions."""

    def test_day_of_week(self, frozen_time, item_factory):
        """Test parsing with day of week."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture  # Wednesday

        item = item_factory("~ task @s tue")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"

    def test_saturday_friday(self, frozen_time, item_factory):
        """Test parsing weekend days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture  # Wednesday

        item = item_factory("* weekend event @s sat 7p @e 2d2h30m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
