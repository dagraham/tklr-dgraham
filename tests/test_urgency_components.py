import pytest


@pytest.mark.integration
def test_record_urgency_components_include_weight_breakdown(
    test_controller, item_factory, freeze_at
):
    with freeze_at("2025-01-10 12:00:00"):
        item = item_factory(
            "~ submit report @s 2025-01-10 14:00 @p 1 @e 30m @d write and send"
        )
        assert item.parse_ok, item.parse_message
        record_id = test_controller.add_item(item)
        test_controller.db_manager.populate_dependent_tables(force=True)

        title, lines = test_controller.get_record_urgency_components(record_id)
        body = "\n".join(lines)

        assert title.startswith("Urgency components for")
        assert "urgency:" in body
        assert "components:" in body
        assert "due" in body
        assert "pastdue" in body


@pytest.mark.integration
def test_record_urgency_components_reports_missing_row_for_hidden_task(
    test_controller, item_factory, freeze_at
):
    with freeze_at("2025-01-10 12:00:00"):
        item = item_factory("~ hidden task @s 2025-01-20 10:00 @n 1d")
        assert item.parse_ok, item.parse_message
        record_id = test_controller.add_item(item)
        test_controller.db_manager.populate_dependent_tables(force=True)

        _title, lines = test_controller.get_record_urgency_components(record_id)
        assert lines
        assert "No urgency entry is currently available" in lines[0]
