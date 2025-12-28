import pytest

from tklr.query import QueryEngine, QueryError


def make_record(record_id, itemtype, summary, tokens):
    return {
        "id": record_id,
        "itemtype": itemtype,
        "subject": summary,
        "tokens": tokens,
    }


def test_includes_and_negation():
    engine = QueryEngine()
    records = [
        make_record(
            1,
            "%",
            "Find Waldo",
            [{"t": "@", "k": "d", "token": "@d hidden in plain sight"}],
        ),
        make_record(
            2,
            "~",
            "Another item",
            [{"t": "@", "k": "d", "token": "@d not here"}],
        ),
    ]

    response = engine.run("includes summary waldo", records)
    assert [match.record_id for match in response.matches] == [1]

    response = engine.run("~includes summary waldo", records)
    assert [match.record_id for match in response.matches] == [2]


def test_any_and_equals():
    engine = QueryEngine()
    records = [
        make_record(
            1,
            "*",
            "Blue event",
            [{"t": "@", "k": "t", "token": "@t blue green"}],
        ),
        make_record(
            2,
            "~",
            "Red task",
            [{"t": "@", "k": "t", "token": "@t red"}],
        ),
    ]

    response = engine.run("any t blue green", records)
    assert [match.record_id for match in response.matches] == [1]

    response = engine.run("equals itemtype ~", records)
    assert [match.record_id for match in response.matches] == [2]


def test_dt_comparisons_and_filters():
    engine = QueryEngine()
    records = [
        make_record(
            1,
            "*",
            "Holiday",
            [{"t": "@", "k": "s", "token": "@s 2025-12-25"}],
        ),
        make_record(
            2,
            "~",
            "Meeting",
            [{"t": "@", "k": "s", "token": "@s 2024-06-15 10:00"}],
        ),
    ]

    response = engine.run("dt s ? date", records)
    assert [match.record_id for match in response.matches] == [1]

    response = engine.run("dt s < 2025-01-01", records)
    assert [match.record_id for match in response.matches] == [2]


def test_info_command():
    engine = QueryEngine()
    records = [make_record(5, "~", "Sample", [])]
    response = engine.run("info 5", records)
    assert response.info_id == 5
    assert response.matches == []


def test_invalid_query_raises():
    engine = QueryEngine()
    with pytest.raises(QueryError):
        engine.run("", [])
