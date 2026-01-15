"""
Regression tests for finish-time normalization.

Each test encodes a (submitted, expected) pair pulled from TODO.md so we can
lock in the desired behavior once finish processing is updated. Cases are
marked xfail until the implementation matches the expectations.
"""

from __future__ import annotations

import pytest


def _canonical_tokens(tokens: list[dict]) -> list[tuple[str, str]]:
    """
    Convert Item.tokens into a deterministic representation that is easy to
    compare while staying agnostic of implementation details like positions.
    """
    canonical: list[tuple[str, str]] = []

    for token in tokens:
        token_type = token.get("t")
        token_text = (token.get("token") or "").strip()
        key = token.get("k") or ""

        if token_type == "itemtype":
            canonical.append(("itemtype", token_text))
        elif token_type == "subject":
            canonical.append(("subject", token_text))
        elif token_type in {"@", "&"}:
            canonical.append((f"{token_type}{key}", token_text))

    return canonical


FINISH_CASES = [
    pytest.param(
        "~ test: repeating daily 1 @s 2025-12-04 3:30p @r d &c 2 @f 2025-12-09 10:00a",
        "~ test: repeating daily 1 @s 2025-12-05 3:30p @r d &c 1",
        id="daily-count-decrement",
    ),
    pytest.param(
        "~ test: repeating daily 2 @s 2025-12-05 3:30p @r d &c 1 @f 2025-12-10 11:00a",
        "x test: repeating daily 2 @s 2025-12-05 3:30p",
        id="daily-count-final",
    ),
    pytest.param(
        "~ test: with rdates @s 2025-12-08 1:30p @r d @+ 2025-12-08 9:00a, 2025-12-08 5:00p @f 2025-12-09 10:00a",
        "~ test: with rdates @s 2025-12-08 1:30p @r d @+ 2025-12-08 5:00p",
        id="rrule-with-rdates-drop-earliest",
    ),
    pytest.param(
        "~ test: with rdates @s 2025-12-08 1:30p @r d @+ 2025-12-08 5:00p @f 2025-12-10 8:00a",
        "~ test: with rdates @s 2025-12-09 1:30p @r d @+ 2025-12-08 5:00p",
        id="rrule-with-rdates-advance-start",
    ),
    pytest.param(
        "~ test: offset @s 2025-12-04 12:00p  @o 4d @f 2025-12-08 9:00a",
        "~ test: offset @s 2025-12-12 9:00a @o 4d",
        id="offset-fixed-interval",
    ),
    pytest.param(
        "~ test: offset learn @s 2025-12-04 12:00p @o ~4d @f 2025-12-08 9:00p",
        "~ test: offset learn @s 2025-12-12 11:00p @o ~4d2h",
        id="offset-learning",
    ),
    pytest.param(
        "^ test: project 1 @s 2025-12-08 1:30p @~ job 1 &r 1 &f 2025-12-04 @~ job 2 &s 3w &r 2: 1",
        "^ test: project 1 @s 2025-12-08 1:30p @~ job 1 &r 1 &f 2025-12-04 @~ job 2 &s 3w &r 2: 1",
        id="project-partial-finish",
    ),
    pytest.param(
        "^ test: project 2 @s 2025-12-08 1:30p @~ job 1 &r 1 &f 2025-12-04 9:00a @~ job 2 &s 3w &r 2: 1 &f 2025-12-10 4:00p",
        "x test: project 2 @s 2025-12-08 1:30p @~ job 1 &r 1 @~ job 2 &s 3w &r 2: 1",
        id="project-all-finished",
    ),
]


@pytest.mark.unit
@pytest.mark.parametrize("submitted, expected", FINISH_CASES)
def test_finish_normalization_pairs(submitted, expected, item_factory, frozen_time):
    """
    Parse the user-submitted entry, finalize it, and compare the canonical
    tokens against the separately parsed expectation.
    """
    submitted_item = item_factory(submitted)
    assert submitted_item.parse_ok, f"Parse failed for submitted entry: {submitted_item.parse_message}"

    expected_item = item_factory(expected)
    assert expected_item.parse_ok, f"Parse failed for expected entry: {expected_item.parse_message}"

    actual_tokens = _canonical_tokens(submitted_item.tokens)
    expected_tokens = _canonical_tokens(expected_item.tokens)

    assert actual_tokens == expected_tokens
