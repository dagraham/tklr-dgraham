from __future__ import annotations

import pytest

from tklr.query import QueryEngine, QueryParser, QueryError


def make_record(
    record_id: int,
    summary: str,
    *,
    description: str | None = None,
    tags: list[str] | None = None,
) -> dict:
    tokens: list[dict] = []
    if description:
        tokens.append({"t": "@", "k": "d", "token": f"@d {description}"})
    if tags:
        tokens.append({"t": "@", "k": "t", "token": f"@t {' '.join(tags)}"})
    return {
        "id": record_id,
        "itemtype": "%",
        "subject": summary,
        "tokens": tokens,
    }


def test_query_engine_negation_and_connectors():
    engine = QueryEngine()
    records = [
        make_record(1, "Find Waldo", description="not here"),
        make_record(2, "Find Waldo", description="waldo mentioned"),
        make_record(3, "Missing", description="waldo elsewhere"),
    ]

    response = engine.run("includes summary waldo and ~includes d waldo", records)
    assert [match.record_id for match in response.matches] == [1]


def test_query_engine_any_command_splits_list_fields():
    engine = QueryEngine()
    records = [
        make_record(1, "Paint", tags=["blue", "green"]),
        make_record(2, "Shop", tags=["red"]),
        make_record(3, "Write"),
    ]

    response = engine.run("any t green orange", records)
    assert [match.record_id for match in response.matches] == [1]


def test_query_parser_info_short_circuit():
    parser = QueryParser()
    plan, info_id = parser.parse("info 42")
    assert info_id == 42
    assert plan.is_empty


def test_query_parser_trailing_connector_errors():
    parser = QueryParser()
    with pytest.raises(QueryError):
        parser.parse("includes summary foo and")
