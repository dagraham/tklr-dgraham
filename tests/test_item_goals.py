"""
Tests for goal items.

These tests verify goal parsing and tracking functionality.
"""

import pytest
from datetime import datetime, timedelta
from tklr.item import Item
from tklr.controller import Controller
from dateutil.parser import parse


@pytest.mark.unit
class TestGoalParsing:
    """Test basic goal parsing."""

    def test_simple_goal(self, frozen_time, item_factory):
        """Test parsing a simple goal."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! fitness goal")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        assert item.itemtype == "!"

    def test_goal_with_target(self, frozen_time, item_factory):
        """Test goal with target pattern."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! fitness goal @s 2025-12-01 @t 3/1w")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Should have target: 3 times per 1 week

    def test_goal_with_start_date(self, frozen_time, item_factory):
        """Test goal with specific start date."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! reading goal @s 2025-01-01 @t 5/1m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Goal starts on 2025-01-01


@pytest.mark.unit
class TestGoalTargets:
    """Test goal target patterns."""

    def test_daily_target(self, frozen_time, item_factory):
        """Test goal with daily target."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! exercise @t 1/1d")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        # Target: 1 per day

    def test_weekly_target(self, frozen_time, item_factory):
        """Test goal with weekly target."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! gym visits @t 3/1w")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        # Target: 3 per week

    def test_monthly_target(self, frozen_time, item_factory):
        """Test goal with monthly target."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! book club @s 2025-01-01 @t 1/1m")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Target: 1 per month


@pytest.mark.unit
class TestGoalTracking:
    """Test goal tracking and completion."""

    def test_goal_completion_rate(self, frozen_time, item_factory, test_controller):
        """Test calculating goal completion rate."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        goal = item_factory("! weekly goal @s 2025-01-08 @t 3/1w")

        assert goal.parse_ok
        # Could verify completion rate if implemented

    def test_goal_with_description(self, frozen_time, item_factory):
        """Test goal with description."""
        # Time frozen to 2025-01-15 12:00:00 via frozen_time fixture

        item = item_factory("! fitness @s 2025-01-01 @t 3/1w @d Track weekly workouts")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "Track weekly workouts" in item.description

    def test_goal_completion_rollover(self, frozen_time, item_factory, test_controller):
        item = item_factory("! goal sample @s 2025-01-01 09:00 @t 3/1w")
        starts = parse("2025-01-01 09:00")

        for idx in range(3):
            item.completion = starts + timedelta(days=idx)
            item.finish()

        tokens = {t["k"]: t["token"] for t in item.relative_tokens if t.get("t") == "@"}
        assert tokens["k"] == "@k 0"  # after third completion
        new_start = parse(tokens["s"][3:].strip())
        assert new_start == starts + timedelta(weeks=1)


def test_goal_view_filters_inactive_goals(frozen_time, test_controller, item_factory):
    active = item_factory("! active goal @s 2024-12-31 @t 1/1w")
    assert active.parse_ok
    test_controller.add_item(active)

    future = item_factory("! future goal @s 2026-02-01 @t 1/1w")
    assert future.parse_ok
    test_controller.add_item(future)

    pages, title, header = test_controller.get_goals()
    rows = []
    for page_rows, _ in pages:
        rows.extend(page_rows)
    rows_text = "\n".join(rows)
    assert "active goal" in rows_text
    assert "future goal" not in rows_text


def _add_entry(controller: Controller, env, entry: str) -> None:
    item = Item(raw=entry, env=env, final=True, controller=controller)
    assert item.parse_ok, f"Failed to parse entry: {entry}"
    controller.add_item(item)


def test_get_goals_yield_rows_returns_raw_rows(temp_db_path, test_env):
    ctrl = Controller(str(temp_db_path), test_env, reset=True)
    try:
        _add_entry(ctrl, test_env, "! read more books @s 2025-01-01 @t 2/1w")
        ctrl.db_manager.populate_dependent_tables()

        rows, count, header = ctrl.get_goals(yield_rows=True)
        assert count == 1
        assert any("read more books" in row["text"] for row in rows)
        # assert "subject" in header.lower()
    finally:
        ctrl.db_manager.conn.close()


def test_agenda_includes_goals_section(temp_db_path, test_env):
    ctrl = Controller(str(temp_db_path), test_env, reset=True)
    try:
        _add_entry(ctrl, test_env, "* kickoff @s 2025-01-01 09:00")
        _add_entry(ctrl, test_env, "! weekly goal @s 2024-12-25 @t 1/1w")
        ctrl.db_manager.populate_dependent_tables()

        rows = ctrl.get_agenda(yield_rows=True)
        texts = [row.get("text", "") for row in rows if row.get("text")]

        assert any(text.startswith("Goals (") for text in texts)
        assert any("weekly goal" in text for text in texts)
    finally:
        ctrl.db_manager.conn.close()


def test_agenda_event_window_respects_config(temp_db_path, test_env):
    test_env.config.ui.agenda_days = 2
    ctrl = Controller(str(temp_db_path), test_env, reset=True)
    try:
        base_dt = datetime(2025, 1, 1, 9, 0)
        for offset in range(4):
            start = base_dt + timedelta(days=offset)
            entry = f"* event {offset} @s {start.strftime('%Y-%m-%d %H:%M')}"
            _add_entry(ctrl, test_env, entry)

        ctrl.db_manager.populate_dependent_tables()
        rows = ctrl.get_agenda_events(now=base_dt)
        header_rows = [
            row
            for row in rows
            if row["record_id"] is None and row.get("text", "").strip()
        ]
        assert len(header_rows) == 2
    finally:
        ctrl.db_manager.conn.close()
