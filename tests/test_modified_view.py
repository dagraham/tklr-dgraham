import pytest


@pytest.mark.unit
def test_modified_view_orders_records_desc(test_controller, item_factory):
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
    record_rows = [row for row in rows if row.get("record_id") is not None]
    ordered_ids = [row["record_id"] for row in record_rows]
    assert ordered_ids == [record_ids[1], record_ids[0], record_ids[2]]

    headers = [row["text"] for row in rows if row.get("record_id") is None]
    assert any("Jan 2025" in header for header in headers)
    assert any("Dec 2024" in header for header in headers)

    first_row_text = record_rows[0]["text"]
    assert "[not bold]01-05[/not bold]" in first_row_text
