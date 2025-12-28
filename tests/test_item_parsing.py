"""
Tests for basic Item parsing functionality.

These tests verify that Item objects can correctly parse entry strings
and extract basic attributes like type, summary, priority, etc.
"""

import pytest
from datetime import datetime, date
from tklr.item import Item
from tests.conftest import bin_path_contains_prefix


@pytest.mark.unit
class TestBasicParsing:
    """Test basic parsing of different item types."""

    def test_simple_task(self, item_factory):
        """Test parsing a simple task without any attributes."""
        item = item_factory("~ simple task")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "~"
        assert "simple task" in item.subject

    def test_simple_event(self, item_factory):
        """Test parsing a simple event."""
        item = item_factory("* simple event")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        assert item.itemtype == "*"
        assert "simple event" in item.subject

    def test_simple_journal(self, item_factory):
        """Test parsing a simple journal entry."""
        item = item_factory("% simple journal")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "%"
        assert "simple journal" in item.subject

    def test_draft_item(self, item_factory):
        """Test parsing a draft item."""
        item = item_factory("? draft reminder - no checks")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "?"

    def test_goal_item(self, item_factory):
        """Test parsing a goal item."""
        item = item_factory("! fitness goal")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        assert item.itemtype == "!"


@pytest.mark.unit
class TestPriorities:
    """Test priority parsing."""

    def test_priority_1(self, item_factory):
        """Test parsing priority 1 (highest)."""
        item = item_factory("~ high priority task @p 1")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 1

    def test_priority_2(self, item_factory):
        """Test parsing priority 2."""
        item = item_factory("~ medium priority task @p 2")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 2

    def test_priority_3(self, item_factory):
        """Test parsing priority 3."""
        item = item_factory("~ low priority task @p 3")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 3

    def test_priority_4(self, item_factory):
        """Test parsing priority 4."""
        item = item_factory("~ priority four @p 4")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 4

    def test_priority_5(self, item_factory):
        """Test parsing priority 5 (lowest)."""
        item = item_factory("~ priority five @p 5")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 5

    def test_no_priority(self, item_factory):
        """Test item without explicit priority."""
        item = item_factory("~ no priority task")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Check default priority handling


@pytest.mark.unit
class TestDescriptions:
    """Test description and tag parsing."""

    def test_simple_description(self, item_factory):
        """Test parsing item with description."""
        item = item_factory("~ task with details @d This is a detailed description")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "This is a detailed description" in item.description

    def test_description_with_tags(self, item_factory):
        """Test parsing description with hashtags."""
        item = item_factory("~ task @d Description with #red #white #blue tags")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "Description with" in item.description
        assert "#red" in item.description or "red" in str(item.tags)

    def test_multiline_description(self, frozen_time, item_factory):
        """Test parsing formatted multiline description."""
        # Time frozen to 2025-01-01 12:00:00 via frozen_time fixture

        entry = """% long formatted description @s 2025-01-01
    @d Title
    1. This
       i. with part one
       ii. and this
    2. And finally this.
    """
        item = item_factory(entry)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "Title" in item.description
        assert "This" in item.description


@pytest.mark.unit
class TestBins:
    """Test bin/category parsing."""

    def test_single_bin(self, item_factory):
        """Test parsing item with a single bin."""
        item = item_factory("% item @b work/projects")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.bin_paths is not None
        assert bin_path_contains_prefix(item.bin_paths, ["work", "projects"])
        # assert bin_path_contains_prefix(item.bin_paths, ["projects"])
        assert bin_path_contains_prefix(item.bin_paths, ["work"])

    def test_multiple_bins(self, item_factory):
        """Test parsing item with multiple bins."""
        item = item_factory("~ task @b errands/contexts @b urgent/tags")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.bin_paths is not None
        assert bin_path_contains_prefix(item.bin_paths, ["errands", "contexts"])
        assert bin_path_contains_prefix(item.bin_paths, ["urgent", "tags"])
        # assert ["urgent", "tags"] in item.bin_paths

    def test_complex_bin_path(self, item_factory):
        """Test parsing item with complex bin hierarchy."""
        item = item_factory("% note @b Churchill/quotations/library")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert bin_path_contains_prefix(
            item.bin_paths, ["Churchill", "quotations", "library"]
        )
        assert not bin_path_contains_prefix(item.bin_paths, ["Churchill", "library"])
        assert not bin_path_contains_prefix(item.bin_paths, ["quotations"])
        assert bin_path_contains_prefix(item.bin_paths, ["Churchill", "quotations"])
        assert bin_path_contains_prefix(item.bin_paths, ["Churchill"])

    def test_bin_with_year_month(self, item_factory):
        """Test parsing bin with year/month pattern."""
        item = item_factory("% entry @b 2025:10/2025/journal")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert bin_path_contains_prefix(item.bin_paths, ["2025:10", "2025", "journal"])
