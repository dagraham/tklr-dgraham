from datetime import datetime, timedelta

from tklr.agenda_html import build_agenda_html


def test_agenda_html_expandable_details(test_controller, item_factory):
    day = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    item = item_factory(
        f"* dentist @s {day} 2pm @e 1h @d bring card "
        "@g https://example.com/x @m door code 4321"
    )
    assert item.parse_ok, item.parse_message
    test_controller.add_item(item)
    test_controller.db_manager.populate_dependent_tables()

    page = build_agenda_html(test_controller)

    assert page.startswith("<!DOCTYPE html>")
    assert 'name="viewport"' in page
    assert page.count("<details>") == 1
    assert "bring card" in page
    # @m values are hidden; @g becomes a link; bookkeeping lines are dropped.
    assert "4321" not in page and "door code" not in page
    assert "••••" in page
    assert '<a href="https://example.com/x">' in page
    assert "rruleset" not in page and "instance:" not in page
