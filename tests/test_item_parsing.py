"""
Tests for basic Item parsing functionality.

These tests verify that Item objects can correctly parse entry strings
and extract basic attributes like type, summary, priority, etc.
"""

import pytest
from datetime import datetime, date
from tklr.item import Item
from tests.conftest import bin_path_contains_prefix


@pytest.mark.unit
class TestBasicParsing:
    """Test basic parsing of different item types."""

    def test_simple_task(self, item_factory):
        """Test parsing a simple task without any attributes."""
        item = item_factory("~ simple task")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "~"
        assert "simple task" in item.subject

    def test_simple_event(self, item_factory):
        """Test parsing a simple event."""
        item = item_factory("* simple event")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        assert item.itemtype == "*"
        assert "simple event" in item.subject

    def test_simple_journal(self, item_factory):
        """Test parsing a simple journal entry."""
        item = item_factory("% simple journal")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "%"
        assert "simple journal" in item.subject

    def test_draft_item(self, item_factory):
        """Test parsing a draft item."""
        item = item_factory("? draft reminder - no checks")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.itemtype == "?"

    def test_goal_item(self, item_factory):
        """Test parsing a goal item."""
        item = item_factory("! fitness goal")

        assert not item.parse_ok, (
            f"Parse failed for '{item.entry}': {item.parse_message}"
        )
        assert item.itemtype == "!"


@pytest.mark.unit
class TestPriorities:
    """Test priority parsing."""

    def test_priority_1(self, item_factory):
        """Test parsing priority 1 (highest)."""
        item = item_factory("~ high priority task @p 1")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 1

    def test_priority_2(self, item_factory):
        """Test parsing priority 2."""
        item = item_factory("~ medium priority task @p 2")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 2

    def test_priority_3(self, item_factory):
        """Test parsing priority 3."""
        item = item_factory("~ low priority task @p 3")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 3

    def test_priority_4(self, item_factory):
        """Test parsing priority 4."""
        item = item_factory("~ priority four @p 4")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 4

    def test_priority_5(self, item_factory):
        """Test parsing priority 5 (lowest)."""
        item = item_factory("~ priority five @p 5")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.priority == 5

    def test_no_priority(self, item_factory):
        """Test item without explicit priority."""
        item = item_factory("~ no priority task")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        # Check default priority handling


@pytest.mark.unit
class TestDescriptions:
    """Test description and tag parsing."""

    def test_simple_description(self, item_factory):
        """Test parsing item with description."""
        item = item_factory("~ task with details @d This is a detailed description")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "This is a detailed description" in item.description

    def test_description_with_tags(self, item_factory):
        """Test parsing description with hashtags."""
        item = item_factory("~ task @d Description with #red #white #blue tags")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "Description with" in item.description
        assert "#red" in item.description or "red" in str(item.tags)

    def test_multiline_description(self, frozen_time, item_factory):
        """Test parsing formatted multiline description."""
        # Time frozen to 2025-01-01 12:00:00 via frozen_time fixture

        entry = """% long formatted description @s 2025-01-01
    @d Title
    1. This
       i. with part one
       ii. and this
    2. And finally this.
    """
        item = item_factory(entry)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "Title" in item.description
        assert "This" in item.description

    def test_description_allows_email_address(self, item_factory):
        item = item_factory("~ task @d Contact dnlgrhm@pm.me for follow-up")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "dnlgrhm@pm.me" in item.description
        detail_tokens = [
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "d"
        ]
        assert detail_tokens
        assert "dnlgrhm@pm.me" in detail_tokens[0]["token"]

    def test_non_space_at_is_literal_but_space_at_starts_token(self, item_factory):
        item = item_factory("~ task @d Contact dnlgrhm@pm.me @s 2025-01-01")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert "dnlgrhm@pm.me" in item.description

        at_tokens = [tok for tok in item.relative_tokens if tok.get("t") == "@"]
        keys = [tok.get("k") for tok in at_tokens]
        assert "d" in keys
        assert "s" in keys


@pytest.mark.unit
class TestProjectLiveEditing:
    def test_incomplete_project_job_line_does_not_crash(self, item_factory):
        entry = """^ Project test
  @~ step 1
  @~
  @~ step 3
"""

        item = item_factory(entry, final=False)

        assert item.itemtype == "^"
        assert item.subject == "Project test"
        assert any(tok.get("k") == "~" for tok in item.relative_tokens)

    def test_project_job_requires_r_label_on_final_parse(self, item_factory):
        item = item_factory("^ Project test @~ step 1", final=True)

        assert not item.parse_ok
        assert "Each @~ job requires an &r label" in (item.parse_message or "")

    def test_project_job_missing_r_label_survives_second_finalize(self, item_factory):
        item = item_factory("^ Project test @~ step 1", final=True)
        item.finalize_record()

        assert not item.parse_ok
        assert "Each @~ job requires an &r label" in (item.parse_message or "")

    def test_live_project_schedule_feedback_is_not_hidden_by_missing_job(
        self, item_factory
    ):
        item = item_factory("^ project @s s", final=False)

        assert not item.parse_ok
        assert "Required keys not yet provided" not in (item.parse_message or "")
        assert "Error parsing 's'" in (item.parse_message or "")

    def test_live_project_bare_at_still_shows_required_and_available_keys(
        self, item_factory
    ):
        item = item_factory("^ project @", final=False)

        assert not item.parse_ok
        assert "@ available @-keys:" in (item.parse_message or "")
        assert "required: ~" in (item.parse_message or "")
        assert "optional:" in (item.parse_message or "")

    def test_live_project_rrule_trailing_amp_is_treated_as_incomplete_modifier(
        self, item_factory
    ):
        item = item_factory("^ project @s sat @r m &\n@~ step one", final=False)

        assert not item.parse_ok
        assert "supported frequency" not in (item.parse_message or "")
        assert "repetition &-key: enter &-key" in (item.parse_message or "")


@pytest.mark.unit
class TestInvitees:
    def test_event_invitees_parse(self, item_factory):
        item = item_factory("* planning session @s 2025-01-10 10:00 @i Alice, Bob")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.invitees == ["Alice", "Bob"]

    def test_event_invitees_require_non_empty_names(self, item_factory):
        item = item_factory("* planning session @s 2025-01-10 10:00 @i Alice, , Bob")

        assert not item.parse_ok
        assert item.last_result
        assert "comma separated list of non-empty names" in (item.last_result[1] or "")

    def test_invitees_not_allowed_for_tasks(self, item_factory):
        item = item_factory("~ prepare agenda @i Alice")

        assert not item.parse_ok
        assert "The use of @i is not supported" in (item.parse_message or "")


@pytest.mark.unit
class TestBins:
    """Test bin/category parsing."""

    def test_single_bin(self, item_factory):
        """Test parsing item with a single bin."""
        item = item_factory("% item @b work/projects")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.bin_paths is not None
        assert bin_path_contains_prefix(item.bin_paths, ["work", "projects"])
        # assert bin_path_contains_prefix(item.bin_paths, ["projects"])
        assert bin_path_contains_prefix(item.bin_paths, ["work"])

    def test_multiple_bins(self, item_factory):
        """Test parsing item with multiple bins."""
        item = item_factory("~ task @b errands/contexts @b urgent/tags")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.bin_paths is not None
        assert bin_path_contains_prefix(item.bin_paths, ["errands", "contexts"])
        assert bin_path_contains_prefix(item.bin_paths, ["urgent", "tags"])
        # assert ["urgent", "tags"] in item.bin_paths

    def test_complex_bin_path(self, item_factory):
        """Test parsing item with complex bin hierarchy."""
        item = item_factory("% note @b Churchill/quotations/library")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert bin_path_contains_prefix(
            item.bin_paths, ["Churchill", "quotations", "library"]
        )
        assert not bin_path_contains_prefix(item.bin_paths, ["Churchill", "library"])
        assert not bin_path_contains_prefix(item.bin_paths, ["quotations"])
        assert bin_path_contains_prefix(item.bin_paths, ["Churchill", "quotations"])
        assert bin_path_contains_prefix(item.bin_paths, ["Churchill"])

    def test_bin_with_year_month(self, item_factory):
        """Test parsing bin with year/month pattern."""
        item = item_factory("% entry @b 2025:10/2025/journal")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert bin_path_contains_prefix(item.bin_paths, ["2025:10", "2025", "journal"])


@pytest.mark.unit
class TestLogEntries:
    """Tests for log (-) reminders."""

    def test_log_defaults_schedule(self, frozen_time, item_factory):
        """Log entries without @s should auto-append the current time."""
        entry = "- hydration log"
        item = item_factory(entry)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.auto_log_timestamp is not None

        expected_now = datetime.now().astimezone()
        assert item.auto_log_timestamp == expected_now

        s_tokens = [
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "s"
        ]
        assert len(s_tokens) == 1
        assert "@s" in s_tokens[0]["token"]
        assert item.dtstart_str is not None

    def test_log_respects_explicit_schedule(self, item_factory):
        """If @s is provided, logs should not override it."""
        entry = "- hydration log @s 2025-02-01 09:30"
        item = item_factory(entry)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.auto_log_timestamp is None

        s_tokens = [
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "s"
        ]
        assert len(s_tokens) == 1
        assert "2025-02-01" in s_tokens[0]["token"]
        assert "9:30" in s_tokens[0]["token"]


@pytest.mark.unit
class TestUseLookup:
    """Ensure log-specific @u values come from the use registry."""

    def test_existing_use_parses(self, item_factory, use_factory):
        use_factory("Client Alpha")
        item = item_factory("- call recap @u Client Alpha")

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.use == "Client Alpha"
        assert item.use_id is not None

    def test_unknown_use_suggests(self, item_factory, use_factory):
        use_factory("Jones, Robert")
        use_factory("Jordan, Alex")
        use_factory("John, Sam")
        use_factory("Jules, Max")

        item = item_factory("- phoned client @u J")

        assert not item.parse_ok
        assert item.last_result
        assert "Matching entries:" in (item.last_result[1] or "")
        assert "Jones, Robert" in (item.last_result[1] or "")
        assert "Jordan, Alex" in (item.last_result[1] or "")
        assert "..." in (item.last_result[1] or "")


@pytest.mark.unit
class TestLiveAttributeMatching:
    def test_single_use_match_sets_live_replacement(self, item_factory, use_factory):
        use_factory("exercise.walking")

        item = item_factory("- jog @u e", final=False)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.live_replacement is not None
        assert item.live_replacement[2] == "@u exercise.walking"

    def test_single_context_match_sets_live_replacement(
        self, item_factory, test_controller
    ):
        existing = item_factory("~ existing task @c Errands")
        test_controller.add_item(existing)

        item = item_factory("~ new task @c e", final=False)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.live_replacement is not None
        assert item.live_replacement[2] == "@c Errands"
        context_token = next(
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "c"
        )
        assert "Errands" in context_token.get("_matches", [])

    def test_single_location_match_sets_live_replacement(
        self, item_factory, test_controller
    ):
        existing = item_factory("~ existing task @l Home Office")
        test_controller.add_item(existing)

        item = item_factory("~ new task @l h", final=False)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.live_replacement is not None
        assert item.live_replacement[2] == "@l Home Office"
        location_token = next(
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "l"
        )
        assert "Home Office" in location_token.get("_matches", [])

    def test_single_bin_match_sets_live_replacement(self, item_factory, test_controller):
        seed = item_factory("% filing note @b Churchill/quotations/library")
        test_controller.add_item(seed)

        item = item_factory("~ new task @b chur", final=False)

        assert item.parse_ok, f"Parse failed for '{item.entry}': {item.parse_message}"
        assert item.live_replacement is not None
        assert item.live_replacement[2].startswith("@b Churchill/quotations/library")
        bin_token = next(
            tok
            for tok in item.relative_tokens
            if tok.get("t") == "@" and tok.get("k") == "b"
        )
        assert any(
            match.startswith("Churchill/quotations/library")
            for match in bin_token.get("_matches", [])
        )
