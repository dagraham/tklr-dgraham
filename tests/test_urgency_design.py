from datetime import datetime

from tklr.urgency_design import (
    build_urgency_screening_examples,
    build_urgency_structure_examples,
    compute_urgency_screening_report,
    format_urgency_screening_report,
)


def _assert_design_is_balanced(rows, factors):
    assert len(rows) == 8

    counts = {factor: {"high": 0, "low": 0} for factor in factors}

    for row in rows:
        label = row["label"]
        for factor in factors:
            if f"{factor}+" in label:
                counts[factor]["high"] += 1
            else:
                counts[factor]["low"] += 1

        assert "label" in row
        assert "now" in row
        assert "created" in row
        assert "modified" in row
        assert "due" in row
        assert "extent" in row
        assert "priority_level" in row
        assert "blocking" in row
        assert "tags" in row
        assert "description" in row
        assert "jobs" in row
        assert "pinned" in row

    for factor_counts in counts.values():
        assert factor_counts["high"] == 4
        assert factor_counts["low"] == 4


def test_urgency_screening_examples_are_balanced():
    rows = build_urgency_screening_examples(datetime(2026, 4, 1, 12, 0))
    _assert_design_is_balanced(rows, ["P", "D", "A", "R", "T", "E"])


def test_urgency_structure_examples_are_balanced():
    rows = build_urgency_structure_examples(datetime(2026, 4, 1, 12, 0))
    _assert_design_is_balanced(rows, ["P", "D", "X", "B", "J", "A"])


def test_urgency_screening_report_is_sorted_by_urgency(isolated_env):
    rows = compute_urgency_screening_report(
        isolated_env,
        now_dt=datetime(2026, 4, 1, 12, 0),
    )

    assert len(rows) == 8
    assert rows == sorted(rows, key=lambda row: row["urgency"], reverse=True)

    for row in rows:
        assert "label" in row
        assert "urgency" in row
        assert "percent" in row
        assert "color" in row
        assert "weights" in row
        assert "args" in row


def test_urgency_structure_report_is_sorted_by_urgency(isolated_env):
    rows = compute_urgency_screening_report(
        isolated_env,
        now_dt=datetime(2026, 4, 1, 12, 0),
        design="structure",
    )

    assert len(rows) == 8
    assert rows == sorted(rows, key=lambda row: row["urgency"], reverse=True)

    for row in rows:
        assert "label" in row
        assert "urgency" in row
        assert "percent" in row
        assert "color" in row
        assert "weights" in row
        assert "args" in row


def test_urgency_screening_report_includes_config_summary(isolated_env):
    rows = compute_urgency_screening_report(
        isolated_env,
        now_dt=datetime(2026, 4, 1, 12, 0),
    )
    lines = format_urgency_screening_report(isolated_env, rows)

    text = "\n".join(lines)
    assert "Urgency screening report (base)" in text
    assert "Current urgency settings:" in text
    assert "due:" in text
    assert "pastdue:" in text
    assert "age:" in text
    assert "recent:" in text
    assert "tags:" in text
    assert "description:" in text
    assert "priority:" in text


def test_urgency_structure_report_heading_includes_design_name(isolated_env):
    rows = compute_urgency_screening_report(
        isolated_env,
        now_dt=datetime(2026, 4, 1, 12, 0),
        design="structure",
    )
    lines = format_urgency_screening_report(
        isolated_env,
        rows,
        design="structure",
    )

    text = "\n".join(lines)
    assert "Urgency screening report (structure)" in text
    assert "Current urgency settings:" in text
