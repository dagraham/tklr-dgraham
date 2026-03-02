from datetime import datetime, timedelta

import pytest


def _tag_count(pages):
    return sum(len(tag_map) for _rows, tag_map in pages)


@pytest.mark.unit
def test_modified_view_orders_records_desc(test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    entries = ["% alpha note", "% beta note", "% gamma note"]
    record_ids = []
    for entry in entries:
        item = item_factory(entry)
        assert item.parse_ok
        record_ids.append(test_controller.add_item(item))

    timestamps = [
        "20250102T1200",  # alpha
        "20250105T0830",  # beta (newest)
        "20241215T0915",  # gamma (oldest)
    ]
    cursor = test_controller.db_manager.cursor
    for record_id, ts in zip(record_ids, timestamps, strict=False):
        cursor.execute("UPDATE Records SET modified = ? WHERE id = ?", (ts, record_id))
    test_controller.db_manager.conn.commit()

    rows = test_controller.get_modified(yield_rows=True)
    ordered_ids = [row["record_id"] for row in rows]
    assert ordered_ids == [record_ids[1], record_ids[0], record_ids[2]]

    first_row_text = rows[0]["text"]
    assert "[not bold]25-01-05[/not bold]" in first_row_text


@pytest.mark.unit
def test_modified_view_honors_dayfirst_yearfirst_and_two_digit_year(
    test_controller, item_factory
):
    test_controller.dayfirst = True
    test_controller.yearfirst = False
    test_controller.two_digit_year = False

    item = item_factory("% beta note")
    assert item.parse_ok
    record_id = test_controller.add_item(item)

    cursor = test_controller.db_manager.cursor
    cursor.execute(
        "UPDATE Records SET modified = ? WHERE id = ?",
        ("20250105T0830", record_id),
    )
    test_controller.db_manager.conn.commit()

    rows = test_controller.get_modified(yield_rows=True)
    assert rows
    assert "[not bold]05-01-2025[/not bold]" in rows[0]["text"]


@pytest.mark.unit
def test_modified_view_paginates_when_tags_exhausted(test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = True

    record_ids = []
    for i in range(30):
        item = item_factory(f"% note {i}")
        assert item.parse_ok
        record_ids.append(test_controller.add_item(item))

    base = datetime(2025, 1, 1, 9, 0)
    cursor = test_controller.db_manager.cursor
    for i, record_id in enumerate(record_ids):
        ts = (base + timedelta(minutes=i)).strftime("%Y%m%dT%H%M")
        cursor.execute("UPDATE Records SET modified = ? WHERE id = ?", (ts, record_id))
    test_controller.db_manager.conn.commit()

    pages, _ = test_controller.get_modified()
    assert len(pages) >= 2
    assert _tag_count(pages) == 30


@pytest.mark.unit
def test_modified_view_dims_unchanged_year_month_components(test_controller, item_factory):
    test_controller.dayfirst = False
    test_controller.yearfirst = True
    test_controller.two_digit_year = False

    ids = []
    for entry in ["% note newer", "% note older"]:
        item = item_factory(entry)
        assert item.parse_ok
        ids.append(test_controller.add_item(item))

    cursor = test_controller.db_manager.cursor
    cursor.execute("UPDATE Records SET modified = ? WHERE id = ?", ("20250105T0830", ids[0]))
    cursor.execute("UPDATE Records SET modified = ? WHERE id = ?", ("20250103T0830", ids[1]))
    test_controller.db_manager.conn.commit()

    rows = test_controller.get_modified(yield_rows=True)
    assert len(rows) >= 2
    second_row = rows[1]["text"]
    dim = test_controller.dim_style
    assert f"[{dim}]2025[/{dim}]" in second_row
    assert f"[{dim}]01[/{dim}]" in second_row
