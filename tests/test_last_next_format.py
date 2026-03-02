from datetime import datetime, timedelta

import pytest


def _strip_markup(text: str) -> str:
    import re

    return re.sub(r"\[[^\]]+\]", "", text)


def _record_lines(pages):
    for page_rows, _ in pages:
        for row in page_rows:
            if "[/not bold]   [" in row:
                yield row


def _first_record_line(pages):
    for row in _record_lines(pages):
        return row
    raise AssertionError("No record rows found")


def _tag_count(pages):
    return sum(len(tag_map) for _rows, tag_map in pages)


@pytest.mark.unit
def test_last_view_shows_numeric_ymd_by_default(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    item = item_factory("* past event @s 2024-12-31 09:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_last()
    row_text = _first_record_line(pages)
    assert "24-12-31" in _strip_markup(row_text), row_text
    assert ":" not in row_text


@pytest.mark.unit
def test_next_view_shows_numeric_ymd_by_default(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    item = item_factory("* future event @s 2025-01-05 14:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_next()
    row_text = _first_record_line(pages)
    assert "25-01-05" in _strip_markup(row_text), row_text
    assert ":" not in row_text


@pytest.mark.unit
def test_last_view_honors_dayfirst_yearfirst_and_two_digit_year(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = True
    test_controller.yearfirst = False
    test_controller.two_digit_year = False

    item = item_factory("* past event @s 2024-12-31 09:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_last()
    row_text = _first_record_line(pages)
    assert "31-12-2024" in _strip_markup(row_text), row_text


@pytest.mark.unit
def test_next_view_honors_dayfirst_yearfirst_and_two_digit_year(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = True
    test_controller.yearfirst = False
    test_controller.two_digit_year = False

    item = item_factory("* future event @s 2025-01-05 14:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_next()
    row_text = _first_record_line(pages)
    assert "05-01-2025" in _strip_markup(row_text), row_text


@pytest.mark.unit
def test_next_view_stays_ascending(frozen_time, test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = False

    for when in ["2025-01-05 09:00", "2025-01-03 09:00"]:
        item = item_factory(f"* future event @s {when} z none")
        assert item.parse_ok
        test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_next()
    lines = list(_record_lines(pages))
    assert "2025-01-03" in _strip_markup(lines[0]), lines[0]
    assert "2025-01-05" in _strip_markup(lines[1]), lines[1]
    dim = test_controller.dim_style
    assert f"[{dim}]2025[/{dim}]" in lines[1], lines[1]
    assert f"[{dim}]01[/{dim}]" in lines[1], lines[1]
    assert f"[{dim}]-[/{dim}]" in lines[1], lines[1]


@pytest.mark.unit
def test_last_view_stays_descending(frozen_time, test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = False

    for when in ["2024-12-30 09:00", "2024-12-31 09:00"]:
        item = item_factory(f"* past event @s {when} z none")
        assert item.parse_ok
        test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_last()
    lines = list(_record_lines(pages))
    assert "2024-12-31" in _strip_markup(lines[0]), lines[0]
    assert "2024-12-30" in _strip_markup(lines[1]), lines[1]


@pytest.mark.unit
def test_next_view_paginates_when_tags_exhausted(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    base = datetime(2025, 1, 2, 9, 0)
    for i in range(30):
        when = (base + timedelta(days=i)).strftime("%Y-%m-%d %H:%M")
        item = item_factory(f"* future event {i} @s {when} z none")
        assert item.parse_ok
        test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_next()
    assert len(pages) >= 2
    assert _tag_count(pages) == 30


@pytest.mark.unit
def test_last_view_paginates_when_tags_exhausted(
    frozen_time, test_controller, item_factory
):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    base = datetime(2024, 12, 31, 9, 0)
    for i in range(30):
        when = (base - timedelta(days=i)).strftime("%Y-%m-%d %H:%M")
        item = item_factory(f"* past event {i} @s {when} z none")
        assert item.parse_ok
        test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_last()
    assert len(pages) >= 2
    assert _tag_count(pages) == 30
