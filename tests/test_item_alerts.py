"""
Tests for item alerts and notifications.

These tests verify alert/notification parsing and timing.
"""

import pytest
from datetime import datetime, timedelta
from tklr.item import Item


@pytest.mark.unit
class TestBasicAlerts:
    """Test basic alert functionality."""

    def test_single_alert(self, frozen_time, item_factory):
        """Test item with single alert."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* meeting @s 2025-01-15 14:00 @a 15m"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have alert 15 minutes before

    def test_multiple_alerts(self, frozen_time, item_factory):
        """Test item with multiple alerts."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* alert test @s 2025-01-15 12:05 @a 3m, 1m: v"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have alerts at 3m and 1m before


@pytest.mark.unit
class TestAlertTypes:
    """Test different alert types."""

    def test_visual_alert(self, frozen_time, item_factory):
        """Test visual alert type."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event @s 2025-01-15 12:05 @a 2m: v"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should be visual alert

    def test_notification_alert(self, frozen_time, item_factory):
        """Test notification alert type."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* notify test @s 2025-01-15 12:06 @a 4m, 2m, 0m: n"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should be notification alerts


@pytest.mark.unit
class TestAlertTiming:
    """Test alert timing calculations."""

    def test_alert_minutes_before(self, frozen_time, item_factory):
        """Test alerts specified in minutes."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* meeting @s 2025-01-15 13:00 @a 30m"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Alert should be at 12:30

    def test_alert_hours_before(self, frozen_time, item_factory):
        """Test alerts specified in hours."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event @s 2025-01-16 10:00 @a 2h"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Alert should be at 08:00 next day

    def test_alert_days_before(self, frozen_time, item_factory):
        """Test alerts specified in days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* conference @s 2025-01-20 @a 2d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Alert should be 2 days before

    def test_alert_weeks_before(self, frozen_time, item_factory):
        """Test alerts specified in weeks."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ project deadline @s 2025-02-15 @a 2w"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Alert should be 2 weeks before


@pytest.mark.unit
class TestNoticeAttribute:
    """Test the @n notice attribute (similar to alerts)."""

    def test_notice_days(self, frozen_time, item_factory):
        """Test notice in days."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event with notice @s 2025-01-17 @n 1d"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have notice 1 day before

    def test_notice_weeks(self, frozen_time, item_factory):
        """Test notice in weeks."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "~ task with notice @s 2025-01-22 @n 1w"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
        # Should have notice 1 week before

    def test_notice_on_event(self, frozen_time, item_factory):
        """Test notice on event."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory(
            "* event @s 2025-01-16 @n 1w"
        )

        assert item.parse_ok, f"Parse failed for \'{item.entry}\': {item.parse_message}"
