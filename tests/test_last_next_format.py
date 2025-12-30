import pytest


def _first_record_line(pages):
    for page_rows, _ in pages:
        for row in page_rows:
            if "[/not bold]   [" in row:
                return row
    raise AssertionError("No record rows found")


@pytest.mark.unit
def test_last_view_shows_mm_dd(frozen_time, test_controller, item_factory):
    item = item_factory("* past event @s 2024-12-31 09:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_last()
    row_text = _first_record_line(pages)
    assert "[not bold]12-31[/not bold]" in row_text, row_text
    assert ":" not in row_text


@pytest.mark.unit
def test_next_view_shows_mm_dd(frozen_time, test_controller, item_factory):
    item = item_factory("* future event @s 2025-01-05 14:00 z none")
    assert item.parse_ok
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    pages, _ = test_controller.get_next()
    row_text = _first_record_line(pages)
    assert "[not bold]01-05[/not bold]" in row_text, row_text
    assert ":" not in row_text
