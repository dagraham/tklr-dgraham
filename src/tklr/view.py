from __future__ import annotations
import tklr

from importlib.metadata import version
from .shared import log_msg, display_messages
from datetime import datetime, timedelta, date
from logging import log
from packaging.version import parse as parse_version
from rich import box
from rich.console import Console
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.geometry import Size
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input
from textual.widgets import Label
from textual.widgets import Markdown, Static, Footer, Button, Header
from textual.widgets import Placeholder
import string
import shutil
import asyncio
from tklr.common import get_version
import re

from rich.panel import Panel
from textual.containers import Container

from typing import List, Callable, Optional, Any, Iterable

# details_drawer.py
from textual import events

from textual.events import Key


# tklr_version = version("tklr")
tklr_version = get_version()

# Color hex values for readability (formerly from prompt_toolkit.styles.named_colors)
LEMON_CHIFFON = "#FFFACD"
KHAKI = "#F0E68C"
LIGHT_SKY_BLUE = "#87CEFA"
DARK_GRAY = "#A9A9A9"
LIME_GREEN = "#32CD32"
SLATE_GREY = "#708090"
DARK_GREY = "#A9A9A9"  # same as DARK_GRAY
GOLDENROD = "#DAA520"
DARK_ORANGE = "#FF8C00"
GOLD = "#FFD700"
ORANGE_RED = "#FF4500"
TOMATO = "#FF6347"
CORNSILK = "#FFF8DC"
FOOTER = "#FF8C00"

# App version
VERSION = parse_version(tklr_version)

# Colors for UI elements
DAY_COLOR = LEMON_CHIFFON
FRAME_COLOR = KHAKI
HEADER_COLOR = LIGHT_SKY_BLUE
DIM_COLOR = DARK_GRAY
EVENT_COLOR = LIME_GREEN
AVAILABLE_COLOR = LIGHT_SKY_BLUE
WAITING_COLOR = SLATE_GREY
FINISHED_COLOR = DARK_GREY
GOAL_COLOR = GOLDENROD
CHORE_COLOR = KHAKI
PASTDUE_COLOR = DARK_ORANGE
BEGIN_COLOR = GOLD
DRAFT_COLOR = ORANGE_RED
TODAY_COLOR = TOMATO
# SELECTED_BACKGROUND = "#566573"
SELECTED_BACKGROUND = "#dcdcdc"
MATCH_COLOR = GOLD
TITLE_COLOR = CORNSILK

# This one appears to be a Rich/Textual style string
SELECTED_COLOR = "bold yellow"

ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY
alpha = [x for x in string.ascii_lowercase]

TYPE_TO_COLOR = {
    "*": EVENT_COLOR,  # event
    "-": AVAILABLE_COLOR,  # available task
    "+": WAITING_COLOR,  # waiting task
    "%": FINISHED_COLOR,  # finished task
    "~": GOAL_COLOR,  # goal
    "^": CHORE_COLOR,  # chore
    "<": PASTDUE_COLOR,  # past due task
    ">": BEGIN_COLOR,  # begin
    "!": DRAFT_COLOR,  # draft
}


def _measure_rows(lines: list[str]) -> int:
    """
    Count how many display rows are implied by explicit newlines.
    Does NOT try to wrap, so markup stays safe.
    """
    total = 0
    for block in lines:
        # each newline adds a line visually
        total += len(block.splitlines()) or 1
    return total


def _make_rows(lines: list[str]) -> list[str]:
    new_lines = []
    for block in lines:
        new_lines.extend(block.splitlines())
    return new_lines


def format_date_range(start_dt: datetime, end_dt: datetime):
    """
    Format a datetime object as a week string, taking not to repeat the month name unless the week spans two months.
    """
    same_year = start_dt.year == end_dt.year
    same_month = start_dt.month == end_dt.month
    if same_year and same_month:
        return f"{start_dt.strftime('%B %-d')} - {end_dt.strftime('%-d, %Y')}"
    elif same_year and not same_month:
        return f"{start_dt.strftime('%B %-d')} - {end_dt.strftime('%B %-d, %Y')}"
    else:
        return f"{start_dt.strftime('%B %-d, %Y')} - {end_dt.strftime('%B %-d, %Y')}"


def decimal_to_base26(decimal_num):
    """
    Convert a decimal number to its equivalent base-26 string.

    Args:
        decimal_num (int): The decimal number to convert.

    Returns:
        str: The base-26 representation where 'a' = 0, 'b' = 1, ..., 'z' = 25.
    """
    if decimal_num < 0:
        raise ValueError("Decimal number must be non-negative.")

    if decimal_num == 0:
        return "a"  # Special case for zero

    base26 = ""
    while decimal_num > 0:
        digit = decimal_num % 26
        base26 = chr(digit + ord("a")) + base26  # Map digit to 'a'-'z'
        decimal_num //= 26

    return base26


def get_previous_yrwk(year, week):
    """
    Get the previous (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Subtract 1 week
    previous_monday = monday_date - timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return previous_monday.isocalendar()[:2]


def get_next_yrwk(year, week):
    """
    Get the next (year, week) from an ISO calendar (year, week).
    """
    # Convert the ISO year and week to a Monday date
    monday_date = datetime.strptime(f"{year} {week} 1", "%G %V %u")
    # Add 1 week
    next_monday = monday_date + timedelta(weeks=1)
    # Get the ISO year and week of the new date
    return next_monday.isocalendar()[:2]


def calculate_4_week_start():
    """
    Calculate the starting date of the 4-week period, starting on a Monday.
    """
    today = datetime.now()
    iso_year, iso_week, iso_weekday = today.isocalendar()
    start_of_week = today - timedelta(days=iso_weekday - 1)
    weeks_into_cycle = (iso_week - 1) % 4
    return start_of_week - timedelta(weeks=weeks_into_cycle)


HelpText = f"""\
[bold][{TITLE_COLOR}]TKLR {VERSION}[/{TITLE_COLOR}][/bold]
[bold][{HEADER_COLOR}]Key Bindings[/{HEADER_COLOR}][/bold]
[bold]^Q[/bold]        Quit           [bold]^S[/bold]    Screenshot
[bold][{HEADER_COLOR}]View[/{HEADER_COLOR}][/bold]
 [bold]A[/bold]        Agenda          [bold]R[/bold]    Remaining Alerts 
 [bold]G[/bold]        Goals           [bold]F[/bold]    Find 
 [bold]N[/bold]        Notes           [bold]P[/bold]    Prior 
 [bold]S[/bold]        Scheduled       [bold]U[/bold]    Upcoming 
[bold][{HEADER_COLOR}]Search[/{HEADER_COLOR}][/bold]
 [bold]/[/bold]        Set search      empty search clears
 [bold]>[/bold]        Next match      [bold]<[/bold]    Previous match
[bold][{HEADER_COLOR}]Weeks Navigation[/{HEADER_COLOR}][/bold]
 [bold]Left[/bold]     previous week   [bold]Up[/bold]   up in the list
 [bold]Right[/bold]    next week       [bold]Down[/bold] down in the list
 [bold]S+Left[/bold]   prior 4-weeks   [bold]"."[/bold]  center week
 [bold]S+Right[/bold]  next 4-weeks    [bold]" "[/bold]  current 4-weeks 
[bold][{HEADER_COLOR}]Agenda Navigation[/{HEADER_COLOR}][/bold]
 [bold]tab[/bold]      switch between events and tasks 
[bold][{HEADER_COLOR}]Tags and Item Details[/{HEADER_COLOR}][/bold] 
Each of the views listed above displays a list 
of items. In these listings, each item begins 
with a tag sequentially generated from 'a', 'b',
..., 'z', 'ba', 'bb' and so forth. Press the 
keys of the tag on your keyboard to see the
details of the item and access related commands. 
""".splitlines()


# If you haven’t already defined it, here's the helper:
class ListWithDetails(Container):
    """Container with a main ScrollableList and a bottom details ScrollableList."""

    DEFAULT_CSS = """
    ListWithDetails {
        layout: vertical;
    }
    ListWithDetails > #main-list {
        height: 1fr;
    }
    ListWithDetails > #details-list {
        height: auto;
        max-height: 14;   /* ~14 rows; adjust to taste */
        border: none;
    }
    ListWithDetails > #details-list.hidden {
        display: none;
    }
    """

    def __init__(self, *args, match_color: str = "#ffd75f", **kwargs):
        super().__init__(*args, **kwargs)
        self._main: ScrollableList | None = None
        self._details: ScrollableList | None = None
        self.match_color = match_color

    def compose(self) -> ComposeResult:
        self._main = ScrollableList([], id="main-list")
        self._details = ScrollableList([], id="details-list")
        self._details.add_class("hidden")
        yield self._main
        yield self._details

    # ---- main list passthroughs ----
    def update_list(self, lines: list[str]) -> None:
        log_msg(f"{lines = }")
        self._main.update_list(lines)

    def set_search_term(self, term: str | None) -> None:
        self._main.set_search_term(term)

    def clear_search(self) -> None:
        self._main.clear_search()

    def jump_next_match(self) -> None:
        self._main.jump_next_match()

    def jump_prev_match(self) -> None:
        self._main.jump_prev_match()

    # ---- details control ----
    def show_details(self, title: str, lines: list[str]) -> None:
        # Feed a single list: title, blank, body
        new_lines = _make_rows(lines)
        # body = [f"[b]{title}[/b]", ""] + new_lines
        # body = [
        #     f"[b]{title}[/b]",
        # ] + new_lines
        body = [
            title,
        ] + new_lines
        log_msg(f"{body = }")
        self._details.update_list(body)
        self._details.remove_class("hidden")
        # focus the details so the user can scroll it immediately
        self._details.focus()  # << here

    def hide_details(self) -> None:
        if not self._details.has_class("hidden"):
            self._details.add_class("hidden")
            # return focus to main list
            self._main.focus()

    def has_details_open(self) -> bool:
        return not self._details.has_class("hidden")

    def focus_main(self) -> None:
        self._main.focus()


class DetailsHelpScreen(ModalScreen[None]):
    BINDINGS = [
        ("escape", "app.pop_screen", "Close"),
        ("ctrl+q", "app.quit", "Quit"),
    ]

    def __init__(self, text: str, title: str = "Item Commands"):
        super().__init__()
        self._title = title
        self._text = text

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._title, id="details_title", classes="title-class"),
            Static(self._text, expand=True, id="details_text"),
        )
        yield Footer()


class HelpModal(ModalScreen[None]):
    """Scrollable help overlay."""

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("q", "dismiss", "Close"),
    ]

    def __init__(self, title: str, lines: list[str] | str):
        super().__init__()
        self._title = title
        self._body = lines if isinstance(lines, str) else "\n".join(lines)

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self._title, id="details_title", classes="title-class"),
            ScrollView(
                Static(Text.from_markup(self._body), id="help_body"), id="help_scroll"
            ),
            Footer(),  # your normal footer style
            id="help_layout",
        )

    def on_mount(self) -> None:
        self.set_focus(self.query_one("#help_scroll", ScrollView))

    def action_dismiss(self) -> None:
        self.app.pop_screen()


class EditorScreen(Screen):
    BINDINGS = [
        ("shift+enter", "commit", "Commit"),
        ("ctrl+s", "save", "Save"),
        ("escape", "close", "Back"),
    ]

    # live entry buffer
    entry_text: reactive[str] = reactive("")

    def __init__(
        self, controller, record_id: int | None = None, *, seed_text: str = ""
    ):
        super().__init__()
        self.controller = controller
        self.record_id = record_id
        self.entry_text = seed_text
        self.item = None  # working Item
        self.last_ok_parse = None  # snapshot for commit
        self.error_lines = []  # display in prompt area

    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("", id="ctx_line", classes="title-class"),
            Static("", id="prompt_panel"),
            TextArea(self.entry_text, id="entry_area"),  # ← Enter inserts newlines
            id="editor_layout",
        )

    async def on_mount(self) -> None:
        # context line
        ctx = self._build_context()
        self.query_one("#ctx_line", Static).update(ctx)
        # focus the editor
        self.query_one("#entry_area", Input).focus()
        # do an initial parse
        self._parse_live(self.entry_text)

    def _build_context(self) -> str:
        if self.record_id is None:
            return "New item — type first character (* ~ ^ % + ?), then subject…"
        row = self.controller.db_manager.get_record(self.record_id)
        subj = row[2] or "(untitled)"
        return f"Editing id {self.record_id} — {subj}"

    async def on_input_changed(self, event: Input.Changed) -> None:
        if event.input.id != "entry_area":
            return
        self.entry_text = event.value
        # live, tolerant parse (don’t finalize/normalize here)
        self._parse_live(self.entry_text)

    def _parse_live(self, text: str) -> None:
        from item import Item  # your class

        self.item = Item(text)
        self.error_lines = []
        if not self.item.parse_ok:
            # item.parse_message may be list[str] from your validator; normalize to lines
            msg = self.item.parse_message
            if isinstance(msg, (list, tuple)):
                self.error_lines = [str(x) for x in msg]
            elif msg:
                self.error_lines = [str(msg)]
        # update prompt with either errors or quick help
        prompt = "\n".join(self.error_lines or self._help_lines())
        self.query_one("#prompt_panel", Static).update(prompt)
        # remember last good parse for Commit
        if self.item.parse_ok:
            self.last_ok_parse = self.item

    def _help_lines(self) -> list[str]:
        return [
            "[dim]/? show help  •  Ctrl+S save  •  Ctrl+Enter commit[/dim]",
            "[dim]Type tokens like: @s 2025-08-20 9:00  @r d &i 2  @+ 2025-08-22[/dim]",
        ]

    # Actions
    def action_close(self) -> None:
        self.app.pop_screen()

    def action_save(self) -> None:
        # Save without schedule normalization (draft save)
        if not self.item or not self.item.parse_ok:
            self.app.notify("Cannot save: fix errors first.", severity="warning")
            return
        self._persist(self.item, finalize=False)
        self.app.notify("Saved.", timeout=1.0)

    def action_commit(self) -> None:
        # Normalize schedule (@s/@r/@+/@-) & jobs, then persist
        src = (
            self.last_ok_parse
            if (self.last_ok_parse and self.last_ok_parse.parse_ok)
            else self.item
        )
        if not src or not src.parse_ok:
            self.app.notify("Cannot commit: fix errors first.", severity="warning")
            return
        # IMPORTANT: finalize only on commit
        try:
            src.finalize_rruleset()
            if hasattr(src, "finalize_jobs"):
                src.finalize_jobs(src.jobs)
            # if you keep finalize_completions(), call it here too
        except Exception as e:
            self.app.notify(f"Finalize failed: {e}", severity="error")
            return
        self._persist(src, finalize=True)
        self.app.notify("Committed.", timeout=1.0)
        # Optional: auto-refresh calling view
        self._try_refresh_calling_view()

    def _persist(self, item, *, finalize: bool) -> None:
        if self.record_id is None:
            # create new
            rid = self.controller.db_manager.insert_item(item)  # implement in DB layer
            self.record_id = rid
        else:
            self.controller.db_manager.update_item(self.record_id, item)

    def _try_refresh_calling_view(self) -> None:
        for scr in getattr(self.app, "screen_stack", []):
            if hasattr(scr, "refresh_data"):
                try:
                    scr.refresh_data()
                except Exception:
                    pass


class DetailsScreen(ModalScreen[None]):
    """
    Context-aware details viewer (tuple-based meta).
    - `details`: list[str] from controller.process_tag(); details[0] is the title.
    - Meta is pulled from controller.get_last_details_meta() on mount.
    """

    BINDINGS = [
        ("escape", "close", "Back"),
        ("?", "show_help", "Help"),
        ("ctrl+q", "quit", "Quit"),
        # (all your other bindings with show=False if you want the Footer to only show "? Help")
    ]

    def __init__(self, details: Iterable[str], showing_help: bool = False):
        super().__init__()
        dl = list(details)
        self.title_text: str = dl[0] if dl else "<Details>"
        self.lines: list[str] = dl[1:] if len(dl) > 1 else []
        if showing_help:
            self.footer_content = f"[bold {FOOTER}]esc[/bold {FOOTER}] Back"
        else:
            self.footer_content = f"[bold {FOOTER}]esc[/bold {FOOTER}] Back  [bold {FOOTER}]?[/bold {FOOTER}] Item Commands"

        # meta / flags (populated on_mount)
        self.record_id: Optional[int] = None
        self.itemtype: str = ""  # "~" task, "*" event, etc.
        self.is_task: bool = False
        self.is_event: bool = False
        self.is_goal: bool = False
        self.is_recurring: bool = False  # from rruleset truthiness
        self.is_pinned: bool = False  # task-only
        self.record: Any = None  # original tuple if you need it

    # ---------- helpers ---------
    def _base_title(self) -> str:
        # Strip any existing pin and return the plain title
        return self.title_text.removeprefix("📌 ").strip()

    def _apply_pin_glyph(self) -> None:
        base = self._base_title()
        if self.is_task and self.is_pinned:
            self.title_text = f"📌 {base}"
        else:
            self.title_text = base
        self.query_one("#details_title", Static).update(self.title_text)

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static(self.title_text, id="details_title", classes="title-class"),
            Static("\n".join(self.lines), expand=True, id="details_text"),
            # Static(self.footer_content),
        )
        yield (Static(self.footer_content))
        # yield Footer()

    # ---------- lifecycle ----------
    def on_mount(self) -> None:
        meta = self.app.controller.get_last_details_meta() or {}
        log_msg(f"{meta = }")
        self.record_id = meta.get("record_id")
        self.itemtype = meta.get("itemtype") or ""
        self.is_task = self.itemtype == "~"
        self.is_event = self.itemtype == "*"
        self.is_goal = self.itemtype == "+"
        self.is_recurring = bool(meta.get("rruleset"))
        self.is_pinned = bool(meta.get("pinned")) if self.is_task else False
        self.record = meta.get("record")
        self._apply_pin_glyph()  # ← show 📌 if needed

    # ---------- actions (footer bindings) ----------
    def action_quit(self) -> None:
        self.app.action_quit()

    def action_close(self) -> None:
        self.app.pop_screen()

    def action_show_help(self) -> None:
        self.app.push_screen(DetailsHelpScreen(self._build_help_text()))

    # ---------- key handling for detail commands ----------
    def on_key(self, event) -> None:
        log_msg(f"{event.key = }")
        k = (event.key or "").lower()

        if k == "e":  # Edit
            self._edit_item()
            return
        if k == "c":  # Edit Copy
            self._copy_item()
            return
        if k == "d":  # Delete (scope depends on recurrence)
            self._delete_item()
            return
        if k == "f" and self.is_task:  # Finish task
            self._finish_task()
            return
        if k == "p":  # Toggle pinned (task-only; no-op otherwise)
            self._toggle_pinned()
            return
        if k == "s":  # Schedule new
            self._schedule_new()
            return
        if k == "r":  # Reschedule
            self._reschedule()
            return
        if k == "t":  # Touch (update modified)
            self._touch_item()
            return

        # ctrl bindings
        if event.key == "ctrl+r" and self.is_recurring:
            self._show_repetitions()
            return

        # if event.key == "ctrl+c" and self.is_task:
        #     self._show_completions()
        #     return

    # ---------- wire these to your controller ----------
    def _edit_item(self) -> None:
        # e.g. self.app.controller.edit_record(self.record_id)
        pass

    def _copy_item(self) -> None:
        # e.g. self.app.controller.copy_record(self.record_id)
        pass

    def _delete_item(self) -> None:
        # e.g. self.app.controller.delete_record(self.record_id, scope=...)
        pass

    # def _finish_task(self) -> None:
    #     if not self.is_task or self.record_id is None:
    #         return
    #
    #     try:
    #         res = self.app.controller.finish_current_instance(self.record_id)
    #         # Nice little confirmation
    #         title = self._base_title()
    #         self.app.notify(f"Finished: {title}", timeout=1.5)
    #
    #         # If it's now fully finished, update the title glyph too
    #         # (optional; your finish may flip to itemtype 'x')
    #         self._apply_pin_glyph()
    #
    #         # ★ Refresh any open screen that knows how to reload itself (Agenda, etc.)
    #
    #         for scr in list(getattr(self.app, "screen_stack", [])):
    #             if scr.__class__.__name__ == "AgendaScreen" and getattr(
    #                 scr, "refresh_data", None
    #             ):
    #                 scr.refresh_data()
    #                 break
    #
    #         # Optionally auto-close the details modal
    #         self.app.pop_screen()
    #
    #     except Exception as e:
    #         self.app.notify(f"Finish failed: {e}", severity="error", timeout=3)

    # def _finish_task(self) -> None:
    #     if not self.is_task or self.record_id is None:
    #         return
    #     try:
    #         res = self.app.controller.finish_current_instance(self.record_id)
    #         note = "Finished" + (" (final)" if res.get("final") else "")
    #         self.app.notify(note, timeout=1.2)
    #         # Refresh Agenda immediately
    #         for scr in getattr(self.app, "screen_stack", []):
    #             if hasattr(scr, "refresh_data"):
    #                 scr.refresh_data()
    #     except Exception as e:
    #         self.app.notify(f"Finish failed: {e}", severity="error")

    def _prompt_finish_datetime(self) -> datetime | None:
        """
        Tiny blocking prompt:
        - Enter -> accept default (now)
        - Esc/empty -> cancel
        - Otherwise parse with dateutil
        Replace with your real prompt widget if you have one.
        """
        default = datetime.utcnow()
        default_str = default.strftime("%Y-%m-%d %H:%M")
        try:
            # If you have a modal/prompt helper, use it; otherwise, Python input() works in a pinch.
            user = self.app.prompt(  # <— replace with your TUI prompt helper if you have one
                f"Finish when? (Enter = {default_str}, Esc = cancel): "
            )
        except Exception:
            # Fallback to stdin
            user = input(
                f"Finish when? (Enter = {default_str}, type 'esc' to cancel): "
            ).strip()

        if user is None:
            return None
        s = str(user).strip()
        if not s:
            return default
        if s.lower() in {"esc", "cancel", "c"}:
            return None
        try:
            return parse_dt(s)
        except Exception as e:
            self.app.notify(f"Couldn’t parse that date/time ({e.__class__.__name__}).")
            return None

    def _finish_task(self) -> None:
        """
        Called on 'f' from DetailsScreen.
        Gathers record/job context, prompts for completion time, calls controller.
        """
        meta = self.app.controller.get_last_details_meta() or {}
        record_id = meta.get("record_id")
        job_id = meta.get("job_id")  # may be None for non-project tasks

        if not record_id:
            self.app.notify("No record selected.")
            return

        dt = datetime.now()
        # dt = self._prompt_finish_datetime()
        if dt is None:
            self.app.notify("Finish cancelled.")
            return

        try:
            res = self.app.controller.finish_from_details(record_id, job_id, dt)
            # res is a dict: {record_id, final, due_ts, completed_ts, new_rruleset}
            if res.get("final"):
                self.app.notify("Finished ✅ (no more occurrences).")
            else:
                self.app.notify("Finished this occurrence ✅.")
            # refresh the list(s) so the item disappears/moves immediately
            if hasattr(self.app.controller, "populate_dependent_tables"):
                self.app.controller.populate_dependent_tables()
            if hasattr(self.app, "refresh_current_view"):
                self.app.refresh_current_view()
            elif hasattr(self.app, "switch_to_same_view"):
                self.app.switch_to_same_view()
        except Exception as e:
            self.app.notify(f"Finish failed: {e}")

    def _toggle_pinned(self) -> None:
        if not self.is_task or self.record_id is None:
            return
        new_state = self.app.controller.toggle_pin(self.record_id)
        self.is_pinned = bool(new_state)
        self.app.notify("Pinned" if self.is_pinned else "Unpinned", timeout=1.2)

        self._apply_pin_glyph()  # ← update title immediately

        # Optional: refresh Agenda if present so list order updates
        for scr in getattr(self.app, "screen_stack", []):
            if scr.__class__.__name__ == "AgendaScreen" and hasattr(
                scr, "refresh_data"
            ):
                scr.refresh_data()
                break

    def _schedule_new(self) -> None:
        # e.g. self.app.controller.schedule_new(self.record_id)
        pass

    def _reschedule(self) -> None:
        # e.g. self.app.controller.reschedule(self.record_id)
        pass

    def _touch_item(self) -> None:
        # e.g. self.app.controller.touch_record(self.record_id)
        pass

    def _show_repetitions(self) -> None:
        if not self.is_recurring or self.record_id is None:
            return
        # e.g. rows = self.app.controller.list_repetitions(self.record_id)
        pass

    def _show_completions(self) -> None:
        if not self.is_task or self.record_id is None:
            return
        # e.g. rows = self.app.controller.list_completions(self.record_id)
        pass

    # ---------- contextual help ----------
    def _build_help_text(self) -> str:
        left, right = [], []

        left.append("[bold] e[/bold] Edit")
        left.append("[bold] c[/bold] Edit Copy")
        left.append("[bold] d[/bold] Delete")

        right.append("[bold] r[/bold] Reschedule")
        right.append("[bold] s[/bold] Schedule New")
        right.append("[bold] t[/bold] Touch")

        if self.is_task:
            left.append("[bold] f[/bold] Finish")
            right.append("[bold] p[/bold] Toggle Pinned ")
        if self.is_recurring:
            left.append("[bold]^r[/bold] Repetitions")

        # balance columns
        m = max(len(left), len(right))
        left += [""] * (m - len(left))
        right += [""] * (m - len(right))

        lines = [
            f"[bold {GOLD}]{self.title_text}[/bold {GOLD}]",
            "",
        ]
        for l, r in zip(left, right):
            lines.append(f"{l:<32} {r}" if r else l)
        return "\n".join(lines)


class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, lines: list[str], footer: str = ""):
        super().__init__()
        self._title = lines[0]
        self._lines = lines[1:]
        self._footer = footer or f"[bold {FOOTER}]esc[/bold {FOOTER}] Back"

    def compose(self):
        yield Vertical(
            Static(self._title, id="details_title", classes="title-class"),
            ScrollableList(self._lines, id="help_list"),
            Static(self._footer, id="custom_footer"),
            id="help_layout",
        )

    def on_mount(self):
        # Make sure it fills the screen; no popup sizing/margins.
        self.styles.width = "100%"
        self.styles.height = "100%"
        self.query_one("#help_layout").styles.height = "100%"
        self.query_one("#help_list", ScrollableList).styles.height = "1fr"


class ScrollableList(ScrollView):
    """A scrollable list widget with title-friendly rendering and search.

    Features:
      - Efficient virtualized rendering (line-by-line).
      - Simple search with highlight.
      - Jump to next/previous match.
      - Easy list updating via `update_list`.
    """

    def __init__(
        self, lines: List[str], *, match_color: str = MATCH_COLOR, **kwargs
    ) -> None:
        super().__init__(**kwargs)
        self.console = Console()
        self.match_color = match_color

        # Backing store
        self.lines: List[Text] = [Text.from_markup(line) for line in lines]

        # Virtual size: width is terminal width minus small gutter; height = #lines
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))

        # Search state
        self.search_term: Optional[str] = None
        self.matches: List[int] = []
        self.current_match_idx: int = -1

    # ---------- Public API ----------

    def update_list(self, new_lines: List[str]) -> None:
        """Replace the list content and refresh."""
        log_msg(f"{new_lines = }")
        self.lines = [Text.from_markup(line) for line in new_lines]
        log_msg(f"{self.lines = }")
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))
        # Clear any existing search (content likely changed)
        self.clear_search()
        self.refresh()

    def set_search_term(self, search_term: Optional[str]) -> None:
        """Apply a new search term, highlight all matches, and jump to the first."""
        self.clear_search()  # resets matches and index
        term = (search_term or "").strip().lower()
        if not term:
            self.refresh()
            return

        self.search_term = term
        self.matches = [
            i for i, line in enumerate(self.lines) if term in line.plain.lower()
        ]
        if self.matches:
            self.current_match_idx = 0
            self.scroll_to(0, self.matches[0])
        self.refresh()

    def clear_search(self) -> None:
        """Clear current search term and highlights."""
        self.search_term = None
        self.matches = []
        self.current_match_idx = -1
        self.refresh()

    def jump_next_match(self) -> None:
        """Jump to the next match (wraps)."""
        if not self.matches:
            return
        self.current_match_idx = (self.current_match_idx + 1) % len(self.matches)
        self.scroll_to(0, self.matches[self.current_match_idx])
        self.refresh()

    def jump_prev_match(self) -> None:
        """Jump to the previous match (wraps)."""
        if not self.matches:
            return
        self.current_match_idx = (self.current_match_idx - 1) % len(self.matches)
        self.scroll_to(0, self.matches[self.current_match_idx])
        self.refresh()

    # ---------- Rendering ----------

    def render_line(self, y: int) -> Strip:
        """Render a single virtual line at viewport row y."""
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y

        # Out of bounds -> blank
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)

        # Copy so we can stylize without mutating the source
        line_text = self.lines[y].copy()

        # Highlight if this line is a match
        if self.search_term and y in self.matches:
            line_text.stylize(f"bold {self.match_color}")

        segments = list(line_text.render(self.console))
        # Fit to width
        cropped_segments = Segment.adjust_line_length(
            segments, self.size.width, style=None
        )
        return Strip(cropped_segments, self.size.width)


class SearchableScreen(Screen):
    """Base class for screens that support search on a list widget."""

    def get_search_target(self) -> ScrollableList:
        """Return the ScrollableList to search.
        Default: the '#list' widget, so WeeksScreen keeps working.
        AgendaScreen will override this to point at its active pane.
        """
        return self.query_one("#list", ScrollableList)

    def perform_search(self, term: str):
        try:
            target = self.get_search_target()
            target.set_search_term(term)
            target.refresh()
        except NoMatches:
            pass

    def clear_search(self):
        try:
            target = self.get_search_target()
            target.clear_search()
            target.refresh()
        except NoMatches:
            pass

    def scroll_to_next_match(self):
        try:
            target = self.get_search_target()
            y = target.scroll_offset.y
            nxt = next((i for i in target.matches if i > y), None)
            if nxt is not None:
                target.scroll_to(0, nxt)
                target.refresh()
        except NoMatches:
            pass

    def scroll_to_previous_match(self):
        try:
            target = self.get_search_target()
            y = target.scroll_offset.y
            prv = next((i for i in reversed(target.matches) if i < y), None)
            if prv is not None:
                target.scroll_to(0, prv)
                target.refresh()
        except NoMatches:
            pass


class WeeksScreen(SearchableScreen):
    """4-week grid with a bottom details panel, powered by ListWithDetails."""

    def __init__(
        self,
        title: str,
        table: str,
        list_title: str,
        details: list[str],
        footer_content: str,
    ):
        super().__init__()
        self.table_title = title
        self.table = table
        self.list_title = list_title
        self.details = details
        self.footer_content = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.list_with_details: ListWithDetails | None = None

    # Let global search target the currently-focused list
    def get_search_target(self):
        if not self.list_with_details:
            return None
        return (
            self.list_with_details._details
            if self.list_with_details.has_details_open()
            else self.list_with_details._main
        )

    def compose(self) -> ComposeResult:
        yield Static(
            self.table_title or "Untitled",
            id="table_title",
            classes="title-class",
        )
        yield Static(
            self.table or "[i]No data[/i]",
            id="table",
            classes="weeks-table",
        )
        yield Static(self.list_title, id="list_title", classes="title-class")

        # Main list + bottom details (scrollable) in one container
        self.list_with_details = ListWithDetails(id="list")
        yield self.list_with_details

        yield Static(self.footer_content)

    async def on_mount(self) -> None:
        # seed list content
        if self.list_with_details:
            # details[0] is the list title; details[1:] are lines
            self.list_with_details.update_list(self.details[1:] if self.details else [])

    def update_table_and_list(self):
        # Rebuild from controller (called when week changes / navigations)
        title, table, details = self.app.controller.get_table_and_list(
            self.app.current_start_date, self.app.selected_week
        )
        self.query_one("#table_title", Static).update(title)
        self.query_one("#table", Static).update(table)
        self.query_one("#list_title", Static).update(details[0])

        if self.list_with_details:
            # refresh main lines and hide any open details
            self.list_with_details.update_list(details[1:])
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()

    # Called from DynamicViewApp.on_key when a tag is completed
    def show_details_for_tag(self, tag: str) -> None:
        app = self.app  # DynamicViewApp
        parts = app.controller.process_tag(tag, "week", app.selected_week)
        if not parts:
            return
        title, lines = parts[0], parts[1:]
        if self.list_with_details:
            self.list_with_details.show_details(title, lines)

    # quality-of-life: Esc hides details
    def on_key(self, event):
        if event.key == "escape" and self.list_with_details:
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()
                event.stop()


class AgendaScreen(SearchableScreen):
    BINDINGS = [
        ("tab", "toggle_pane", "Switch Pane"),
        ("r", "refresh", "Refresh"),
        ("A", "refresh", "Agenda"),
        ("escape", "hide_details", "Hide Details"),
    ]

    def __init__(self, controller, footer: str = ""):
        super().__init__()
        self.controller = controller
        self.footer_text = (
            f"[{FOOTER}]?[/{FOOTER}] Help  "
            f"[bold {FOOTER}]/[/bold {FOOTER}] Search  "
            f"[bold {FOOTER}]tab[/bold {FOOTER}] events <-> tasks"
        )
        self.active_pane = "tasks"
        self.events_view: ListWithDetails | None = None
        self.tasks_view: ListWithDetails | None = None
        self.events = {}
        self.tasks = []

    # SearchableScreen will call this for search routing
    def get_search_target(self) -> ScrollableList:
        return (
            self.tasks_view._main
            if self.active_pane == "tasks"
            else self.events_view._main
        )

    def compose(self) -> ComposeResult:
        self.events_view = ListWithDetails(id="events")
        self.tasks_view = ListWithDetails(id="tasks")
        yield Vertical(
            Container(
                Static("Events", id="events_title"),
                self.events_view,
                id="events-pane",
            ),
            Container(
                Static("Tasks", id="tasks_title"),
                self.tasks_view,
                id="tasks-pane",
            ),
            Static(self.footer_text),
            id="agenda-layout",
        )

    def on_mount(self) -> None:
        self.refresh_data()
        self._activate_pane("tasks")

    def _activate_pane(self, which: str):
        self.active_pane = which
        # focus the main list of the active pane
        (self.tasks_view if which == "tasks" else self.events_view).focus_main()
        self.app.view = which
        ev = self.query_one("#events_title", Static)
        tk = self.query_one("#tasks_title", Static)
        if which == "events":
            tk.add_class("inactive")
            ev.remove_class("inactive")
        else:
            ev.add_class("inactive")
            tk.remove_class("inactive")

    def action_toggle_pane(self):
        self._activate_pane("events" if self.active_pane == "tasks" else "tasks")

    def action_hide_details(self):
        target = self.tasks_view if self.active_pane == "tasks" else self.events_view
        target.hide_details()

    def action_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        try:
            self.events = self.controller.get_agenda_events(datetime.now())
        except TypeError:
            self.events = self.controller.get_agenda_events()
        self.tasks = self.controller.get_agenda_tasks()
        self.update_display()

    def update_display(self):
        # events
        event_lines = []
        for d, entries in self.events.items():
            event_lines.append(f"[bold]{d.strftime('%a %b %-d')}[/bold]")
            for tag, label, subject in entries:
                entry = f"{label} {subject}" if label and label.strip() else subject
                event_lines.append(f"{tag} {entry}".rstrip())
        self.events_view.update_list(event_lines)

        # tasks
        task_lines = []
        for urgency, color, tag, subject in self.tasks:
            task_lines.append(f"{tag} {urgency} {subject}")
        self.tasks_view.update_list(task_lines)

    # called by the app when the user types a tag (base-26)
    def show_details_for_tag(self, tag: str) -> None:
        # Which pane are we in?
        pane_view = self.tasks_view if self.active_pane == "tasks" else self.events_view
        view_name = "tasks" if self.active_pane == "tasks" else "events"

        parts = self.controller.process_tag(tag, view_name, None)
        if not parts:
            self.notify(f"Unknown tag '{tag}'", severity="warning")
            return
        title, lines = parts[0], parts[1:]
        log_msg(f"{title = }, {lines = }")
        pane_view.show_details(title, lines)


class FullScreenList(SearchableScreen):
    """Reusable full-screen list for Last, Next, and Find views."""

    def __init__(
        self,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        if details:
            self.title = details[0]
            self.header = details[1] if len(details) > 1 else ""
            self.lines = details[2:] if len(details) > 2 else []
        else:
            self.title, self.header, self.lines = "Untitled", "", []
        self.footer_content = footer_content
        self.list_with_details: ListWithDetails | None = None

    # let global search target the currently-focused list
    def get_search_target(self):
        if not self.list_with_details:
            return None
        # if details is open, search/scroll that; otherwise main list
        return (
            self.list_with_details._details
            if self.list_with_details.has_details_open()
            else self.list_with_details._main
        )

    def compose(self) -> ComposeResult:
        yield Static(self.title, id="scroll_title", expand=True, classes="title-class")
        if self.header:
            yield Static(
                self.header, id="scroll_header", expand=True, classes="header-class"
            )
        self.list_with_details = ListWithDetails(id="list")
        yield self.list_with_details
        yield Static(self.footer_content, id="custom_footer")

    def on_mount(self) -> None:
        if self.list_with_details:
            self.list_with_details.update_list(self.lines)

    # Called by DynamicViewApp.on_key -> screen.show_details_for_tag(tag)
    def show_details_for_tag(self, tag: str) -> None:
        app = self.app  # DynamicViewApp
        parts = app.controller.process_tag(
            tag,
            app.view,
            getattr(app, "selected_week", (0, 0)),  # ignored for these views
        )
        if not parts:
            return
        title, lines = parts[0], parts[1:]
        if self.list_with_details:
            self.list_with_details.show_details(title, lines)

    # Escape to hide details, then return focus to main
    def on_key(self, event):
        if event.key == "escape" and self.list_with_details:
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()
                event.stop()


class DynamicViewApp(App):
    """A dynamic app that supports temporary and permanent view changes."""

    CSS_PATH = "view_textual.css"

    digit_buffer = reactive([])
    # afill = 1
    search_term = reactive("")

    BINDINGS = [
        (".", "center_week", ""),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        ("left", "previous_week", ""),
        ("right", "next_week", ""),
        ("ctrl+s", "take_screenshot", "Take Screenshot"),
        ("escape", "close_details", "Close details"),
        ("R", "show_alerts", "Show Alerts"),
        ("A", "show_agenda", "Show Agenda"),
        ("L", "show_last", "Show Last"),
        ("N", "show_next", "Show Next"),
        ("F", "show_find", "Find"),
        ("S", "show_weeks", "Scheduled"),
        ("?", "show_help", "Help"),
        ("ctrl+q", "quit", "Quit"),
        ("/", "start_search", "Search"),
        (">", "next_match", "Next Match"),
        ("<", "previous_match", "Previous Match"),
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.title = ""
        self.view_mode = "list"
        self.view = "week"
        self.saved_lines = []
        self.afill = 1
        self.details_drawer: DetailsDrawer | None = None
        # log_msg(f"{self.afill = }")

    def set_afill(self, *_args, **_kwargs):
        # Prefer controller’s chosen width, fallback to infer from existing tags
        if self.view == "week":
            fill = self.controller.afill_by_week.get(self.selected_week)
        else:
            fill = self.controller.afill_by_view.get(self.view)
        if fill:
            self.afill = fill
            log_msg(f"using {self.afill = } from controller for {self.view = }")
            return fill
        mapping = self.controller.list_tag_to_id.get(self.view, {})
        if mapping:
            self.afill = len(next(iter(mapping.keys())))  # infer from first key
            log_msg(f"using {self.afill = } from keys for {self.view = }")

    async def on_mount(self):
        # mount the drawer (hidden by default)
        # self.details_drawer = DetailsDrawer()
        # when the drawer closes, put focus back where it belongs
        # self.details_drawer.on_close = self._return_focus_to_active_screen
        # self.mount(self.details_drawer)

        # open default screen
        self.action_show_weeks()

        # your alert timers as-is
        now = datetime.now()
        seconds_to_next = (6 - (now.second % 6)) % 6
        await asyncio.sleep(seconds_to_next)
        self.set_interval(6, self.check_alerts)

    def _return_focus_to_active_screen(self) -> None:
        screen = self.screen
        # if screen exposes a search target (your panes do), focus it; otherwise noop
        try:
            if hasattr(screen, "get_search_target"):
                self.set_focus(screen.get_search_target())
        except Exception:
            pass

    def _resolve_tag_to_record(self, tag: str) -> tuple[int | None, int | None]:
        """
        Return (record_id, job_id) for the current view + tag, or (None, None).
        """
        log_msg(f"{self.view = }, {tag = }")
        mapping = None
        if self.view == "week":
            log_msg(f"{self.selected_week = }, {self.controller.week_tag_to_id = }")
            mapping = self.controller.week_tag_to_id.get(self.selected_week, None)
        else:
            log_msg(f"{self.view = }, {self.controller.list_tag_to_id = }")
            mapping = self.controller.list_tag_to_id.get(self.view, None)

        if not mapping:
            return None, None
        meta = mapping.get(tag, {})
        return meta.get("record_id"), meta.get("job_id")

    def open_details_for_tag(self, tag: str) -> None:
        parts = self.controller.process_tag(tag, self.view, self.selected_week)
        if not parts:
            self.notify(f"Unknown tag '{tag}'", severity="warning")
            return
        title, lines = parts[0], parts[1:]

        drawer = self._ensure_screen_drawer()
        drawer.open_lines(title=title, lines=lines)  # shows and focuses

    def _resolve_tag_to_record(self, tag: str) -> tuple[int | None, int | None]:
        """
        Return (record_id, job_id) for the current view + tag, or (None, None).
        NOTE: uses week_tag_to_id for 'week' view, list_tag_to_id otherwise.
        """
        if self.view == "week":
            mapping = self.controller.week_tag_to_id.get(self.selected_week, {})
        else:
            mapping = self.controller.list_tag_to_id.get(self.view, {})

        meta = mapping.get(tag)
        if not meta:
            return None, None
        if isinstance(meta, dict):
            return meta.get("record_id"), meta.get("job_id")
        # backward compatibility (old mapping was tag -> record_id)
        return meta, None

    def open_details_for_tag(self, tag: str) -> None:
        drawer = self._ensure_screen_drawer()  # your mount/reuse helper
        parts = self.controller.process_tag(tag, self.view, self.selected_week)
        if not parts:
            self.notify(f"Unknown tag '{tag}'", severity="warning")
            return
        drawer.open_from_parts(parts)  # title = parts[0], lines = parts[1:]

    def action_close_details(self):
        screen = self.screen
        drawer = getattr(screen, "details_drawer", None)
        if drawer and not drawer.has_class("hidden"):
            drawer.close()

    def _screen_show_details(self, title: str, lines: list[str]) -> None:
        screen = self.screen
        if hasattr(screen, "show_details"):
            # DetailsPaneMixin: show inline at bottom
            screen.show_details(title, lines)
        else:
            # Fallback to your full-screen DetailsScreen if a screen doesn't have the mixin
            from tklr.view import DetailsScreen

            self.push_screen(DetailsScreen([title] + lines))

    def _open_details_for_tag_on_screen(self, tag: str) -> None:
        # Resolve with your existing controller logic
        parts = self.controller.process_tag(tag, self.view, self.selected_week)
        if parts:
            title, lines = parts[0], parts[1:]
            log_msg(f"{lines = }, {len(lines) = }")
            if hasattr(self.screen, "open_details"):
                self.screen.open_details(title, lines)

    def on_key(self, event: events.Key) -> None:
        """Handle global key events (tags, escape, etc.)."""
        log_msg(f"{self.afill = }")

        if event.key in "abcdefghijklmnopqrstuvwxyz":
            self.digit_buffer.append(event.key)
            if len(self.digit_buffer) == self.afill:
                base26_tag = "".join(self.digit_buffer)
                self.digit_buffer.clear()
                # new: ask the current screen to show details if it supports it
                screen = self.screen
                log_msg(f"{base26_tag = }, {screen = }")
                if hasattr(screen, "show_details_for_tag"):
                    screen.show_details_for_tag(base26_tag)
                else:
                    # fallback: your older flow
                    self.action_show_details(base26_tag)

    def action_take_screenshot(self):
        """Save a screenshot of the current app state."""
        screenshot_path = f"{self.view}_screenshot.svg"
        self.save_screenshot(screenshot_path)
        log_msg(f"Screenshot saved to: {screenshot_path}")

    async def check_alerts(self):
        # called every 6 seconds
        now = datetime.now()
        if now.hour == 0 and now.minute == 0 and 0 <= now.second < 6:
            # populate alerts daily
            self.controller.populate_alerts()
            self.controller.popularte_beginby()
        if now.minute % 10 == 0 and now.second == 0:
            # check alerts every 10 minutes
            self.notify(
                "Checking for scheduled alerts...", severity="info", timeout=1.2
            )
        # execute due alerts
        self.controller.execute_due_alerts()

    def action_show_weeks(self):
        self.view = "week"
        title, table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        list_title = details[0] if details else "Untitled"
        details = details[1:] if details else []
        log_msg(f"{len(details) = }")
        # self.set_afill(details, "action_show_weeks")
        # self.set_afill("week")
        self.set_afill(self.view)
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(WeeksScreen(title, table, list_title, details, footer))

    def action_show_agenda(self):
        self.view = "events"
        details = self.controller.get_agenda_events()
        self.set_afill(self.view)
        log_msg(f"opening agenda view, {self.view = }")
        self.push_screen(AgendaScreen(self.controller))

    def action_show_last(self):
        self.view = "last"
        self.set_afill(self.view)
        details = self.controller.get_last()
        self.set_afill(details, "action_show_last")
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(FullScreenList(details, footer))

    def action_show_next(self):
        self.view = "next"
        self.set_afill(self.view)
        details = self.controller.get_next()
        self.set_afill(details, "action_show_next")

        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(FullScreenList(details, footer))

    def action_show_find(self):
        self.view = "find"
        self.set_afill(self.view)
        search_input = Input(placeholder="Enter search term...", id="find_input")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_show_alerts(self):
        self.view = "alerts"
        self.set_afill(self.view)
        details = self.controller.get_active_alerts()
        log_msg(f"{details = }")
        self.set_afill(details, "alerts")

        footer = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] ESC Back"
        )
        self.push_screen(FullScreenList(details, footer))

    def on_input_submitted(self, event: Input.Submitted):
        search_term = event.value
        event.input.remove()

        if event.input.id == "find_input":
            self.view = "find"
            results = self.controller.find_records(search_term)
            self.set_afill(results, "on_input_submitted")
            footer = "[bold yellow]?[/bold yellow] Help ESC Back / Search"
            self.push_screen(FullScreenList(results, footer))

        elif event.input.id == "search":
            self.perform_search(search_term)

    def action_start_search(self):
        search_input = Input(placeholder="Search...", id="search")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_clear_search(self):
        self.search_term = ""
        screen = self.screen
        if isinstance(screen, SearchableScreen):
            screen.clear_search()
        self.update_footer(search_active=False)

    def action_next_match(self):
        if isinstance(self.screen, SearchableScreen):
            try:
                self.screen.scroll_to_next_match()
            except Exception as e:
                log_msg(f"[Search] Error in next_match: {e}")
        else:
            log_msg("[Search] Current screen does not support search.")

    def action_previous_match(self):
        if isinstance(self.screen, SearchableScreen):
            try:
                self.screen.scroll_to_previous_match()
            except Exception as e:
                log_msg(f"[Search] Error in previous_match: {e}")
        else:
            log_msg("[Search] Current screen does not support search.")

    def perform_search(self, term: str):
        self.search_term = term
        screen = self.screen
        if isinstance(screen, SearchableScreen):
            screen.perform_search(term)
        else:
            log_msg(f"[App] Current screen does not support search.")

    def update_table_and_list(self):
        screen = self.screen
        if isinstance(screen, WeeksScreen):
            screen.update_table_and_list()

    def action_current_period(self):
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.set_afill("week")
        self.update_table_and_list()

    def action_next_period(self):
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.set_afill("week")
        self.update_table_and_list()

    def action_previous_period(self):
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.set_afill("week")
        self.update_table_and_list()

    def action_next_week(self):
        self.selected_week = get_next_yrwk(*self.selected_week)
        if self.selected_week > tuple(
            (self.current_start_date + timedelta(weeks=4) - ONEDAY).isocalendar()[:2]
        ):
            self.current_start_date += timedelta(weeks=1)
        self.set_afill("week")
        self.update_table_and_list()

    def action_previous_week(self):
        self.selected_week = get_previous_yrwk(*self.selected_week)
        if self.selected_week < tuple((self.current_start_date).isocalendar()[:2]):
            self.current_start_date -= timedelta(weeks=1)
        self.set_afill("week")
        self.update_table_and_list()

    def action_center_week(self):
        self.current_start_date = datetime.strptime(
            f"{self.selected_week[0]} {self.selected_week[1]} 1", "%G %V %u"
        ) - timedelta(weeks=1)
        self.update_table_and_list()

    def action_quit(self):
        self.exit()

    def action_show_help(self):
        self.push_screen(HelpScreen(HelpText))

    def action_show_details(self, tag: str):
        record_id, job_id = self._resolve_tag_to_record(tag)
        if not record_id:
            self.notify(f"No item for tag '{tag}'", severity="warning")
            return

        # process_tag returns [title] + field lines
        parts = self.controller.process_tag(tag, self.view, self.selected_week)
        title, lines = parts[0], parts[1:]

        # Open the drawer with exactly what process_tag produced
        self.details_drawer.open_lines(title=title, lines=lines)


if __name__ == "__main__":
    pass
