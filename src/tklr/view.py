from __future__ import annotations
import tklr
import os
import time

from asyncio import create_task

from .shared import log_msg, display_messages, parse
from datetime import datetime, timedelta, date
from logging import log
from packaging.version import parse as parse_version
from rich import box
from rich.console import Console
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.style import Style
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, Grid
from textual.geometry import Size
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.screen import Screen, NoMatches
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input
from textual.widgets import Label
from textual.widgets import Markdown, Static, Footer, Button, Header, Tree
from textual.widgets import Placeholder
from textual.widgets import TextArea
from textual import on
import string
import shutil
import asyncio
from .shared import fmt_user
from typing import Dict, Tuple
import pyperclip
from .item import Item
from .use_system import open_with_default, play_alert_sound

import re

from rich.panel import Panel
from textual.containers import Container

from typing import List, Callable, Optional, Any, Iterable, Tuple

# details_drawer.py
from textual import events

from textual.events import Key
from .versioning import get_version
from pathlib import Path

from dataclasses import dataclass

from .shared import (
    TYPE_TO_COLOR,
)

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
DARK_SALMON = "#E9967A"

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
BIN_COLOR = TOMATO
NOTE_COLOR = DARK_SALMON
NOTICE_COLOR = GOLD

# This one appears to be a Rich/Textual style string
SELECTED_COLOR = "bold yellow"

ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY
alpha = [x for x in string.ascii_lowercase]


# TYPE_TO_COLOR - moved to shared.py


def base26_to_decimal(tag: str) -> int:
    """Decode 'a'..'z' (a=0) for any length."""
    total = 0
    for ch in tag:
        total = total * 26 + (ord(ch) - ord("a"))
    return total


def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).rjust(fill, "a")


def build_details_help(meta: dict) -> list[str]:
    log_msg(f"{meta = }")
    is_task = meta.get("itemtype") == "~"
    is_event = meta.get("itemtype") == "*"
    is_goal = meta.get("itemtype") == "+"
    is_recurring = bool(meta.get("rruleset"))
    is_pinned = bool(meta.get("pinned")) if is_task else False
    subject = meta.get("subject")

    left, rght = [], []
    left.append("[bold],e[/bold] Edit             ")
    left.append("[bold],c[/bold] Copy             ")
    left.append("[bold],d[/bold] Delete           ")
    rght.append("[bold],r[/bold] Reschedule       ")
    rght.append("[bold],n[/bold] Schedule New     ")
    rght.append("[bold],t[/bold] Touch            ")

    if is_task:
        left.append("[bold],f[/bold] Finish           ")
        rght.append("[bold],p[/bold] Toggle Pinned    ")
    if is_recurring:
        left.append("[bold]Ctrl+R[/bold] Show Repetitions ")

    m = max(len(left), len(rght))
    left += [""] * (m - len(left))
    rght += [""] * (m - len(rght))

    lines = [
        f"[bold {TITLE_COLOR}]{meta.get('subject', '- Details -')}[/bold {TITLE_COLOR}]",
        "",
    ]
    for l, r in zip(left, rght):
        lines.append(f"{l}   {r}" if r else l)
    return lines


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
 [bold]B[/bold]        Bins            [bold]F[/bold]    Find 
 [bold]L[/bold]        Last            [bold]N[/bold]    Next  
 [bold]W[/bold]        Weeks           [bold]U[/bold]    Upcoming 
[bold][{HEADER_COLOR}]Search[/{HEADER_COLOR}][/bold]
 [bold]/[/bold]        Set search      empty search clears
 [bold]>[/bold]        Next match      [bold]<[/bold]    Previous match
[bold][{HEADER_COLOR}]Weeks Navigation [/{HEADER_COLOR}][/bold]
 [bold]Left[/bold]     previous week   [bold]Up[/bold]   up in the list
 [bold]Right[/bold]    next week       [bold]Down[/bold] down in the list
 [bold]S+Left[/bold]   4 weeks back    [bold]" "[/bold]  current week 
 [bold]S+Right[/bold]  4 weeks forward [bold]"J"[/bold]  ?jump to date? 
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
#
# tklr/clipboard.py


def timestamped_screenshot_path(
    view: str, directory: str = "screenshots_tmp", ext: str = "svg"
) -> Path:
    Path(directory).mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    return Path(directory) / f"{view}_screenshot-{ts}.{ext}"


class ClipboardUnavailable(RuntimeError):
    """Raised when no system clipboard backend is available for pyperclip."""


def copy_to_clipboard(text: str) -> None:
    """
    Copy text to the system clipboard using pyperclip.

    Raises ClipboardUnavailable if pyperclip cannot access a clipboard backend.
    """
    try:
        pyperclip.copy(text)
    except pyperclip.PyperclipException as e:
        # Give the user an actionable message rather than silently failing.
        raise ClipboardUnavailable(
            "Clipboard operation failed: no system clipboard backend available. "
            "On Linux you may need to install 'xclip', 'xsel' or 'wl-clipboard' "
            "(e.g. 'sudo apt install xclip' or 'sudo pacman -S wl-clipboard'). "
            "If you're running headless (CI/container/SSH) a desktop clipboard may not be present."
        ) from e


def paste_from_clipboard() -> Optional[str]:
    """
    Return clipboard contents, or None if not available.

    Raises ClipboardUnavailable on failure.
    """
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException as e:
        raise ClipboardUnavailable(
            "Paste failed: no system clipboard backend available. "
            "On Linux you may need to install 'xclip', 'xsel' or 'wl-clipboard'."
        ) from e


class BusyWeekBar(Widget):
    """Renders a 7×5 weekly busy bar with aligned day labels."""

    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    colors = {0: "grey35", 1: "yellow", 2: "red"}

    def __init__(self, segments: list[int]):
        assert len(segments) == 35, "Expected 35 slots (7×5)"
        super().__init__()
        self.segments = segments

    def render(self) -> Text:
        # Row 1: labels
        text = Text()
        for d, lbl in enumerate(self.day_labels):
            text.append(f"| {lbl} |", style="bold cyan")
            if d < 6:
                text.append(" ")  # space between columns
        text.append("\n")

        # Row 2: busy/conflict visualization
        for d in range(7):
            day_bits = self.segments[d * 5 : (d + 1) * 5]
            for val in day_bits:
                ch = "█" if val else "░"
                text.append(ch, style=self.colors.get(val, "grey35"))
            if d < 6:
                text.append(" ")  # one space between columns

        return text


class SafeScreen(Screen):
    """Base class that runs post-mount setup safely (after layout is complete)."""

    async def on_mount(self) -> None:
        # Automatically schedule the post-mount hook if defined
        if hasattr(self, "after_mount"):
            # Run a tiny delay to ensure all widgets are fully realized
            self.set_timer(0.01, self.after_mount)


class ListWithDetails(Container):
    """Container with a main ScrollableList and a bottom details ScrollableList."""

    def __init__(self, *args, match_color: str = "#ffd75f", **kwargs):
        super().__init__(*args, **kwargs)
        self._main: ScrollableList | None = None
        self._details: ScrollableList | None = None
        self.match_color = match_color
        self._detail_key_handler: callable | None = None  # ← inject this
        self._details_active = False
        self.details_meta: dict = {}  # ← you already have this

    def on_mount(self):
        # 1) Set the widget backgrounds (outer)
        for w in (self._main, self._details):
            if w and hasattr(w, "styles"):
                w.styles.background = "#373737"

        # 2) Try to set the internal viewport background too (inner)
        def force_scroller_bg(scroller, color: str):
            if not scroller:
                return
            # Newer Textual names
            for attr in ("_viewport", "_window", "_scroll_view", "_view", "_content"):
                vp = getattr(scroller, attr, None)
                if vp and hasattr(vp, "styles"):
                    vp.styles.background = color
                    try:
                        vp.refresh()
                    except Exception:
                        pass

        force_scroller_bg(self._main, "#373737")
        force_scroller_bg(self._details, "#373737")

        # 3) (Optional) make the container itself non-transparent
        if hasattr(self, "styles"):
            self.styles.background = "#373737"

        def _dump_chain(widget):
            w = widget
            depth = 0
            while w is not None:
                try:
                    bg = w.styles.background
                except Exception:
                    bg = "<no styles.background>"
                log_msg(
                    f"depth={depth} id={getattr(w, 'id', None)!r} cls={type(w).__name__} bg={bg}"
                )
                w = getattr(w, "parent", None)
                depth += 1

        try:
            m = self.query_one("#main-list")
            log_msg("=== debug: main-list styles ===")
            log_msg(repr(m.styles))
            _dump_chain(m)
        except Exception as e:
            log_msg(f"debug: couldn't find #main-list: {e}")

    def compose(self):
        # Background filler behind the lists
        # yield Static("", id="list-bg")
        self._main = ScrollableList([], id="main-list")
        self._details = ScrollableList([], id="details-list")
        self._details.add_class("hidden")
        yield self._main
        yield self._details

    def update_list(
        self, lines: list[str], meta_map: dict[str, dict] | None = None
    ) -> None:
        """
        Replace the main list content and (optionally) update the tag→meta mapping.
        `meta_map` is typically controller.list_tag_to_id[view] (or week_tag_to_id[week]).
        """
        self._main.update_list(lines)
        if meta_map is not None:
            self._meta_map = meta_map

    def set_search_term(self, term: str | None) -> None:
        self._main.set_search_term(term)

    def clear_search(self) -> None:
        self._main.clear_search()

    def jump_next_match(self) -> None:
        self._main.jump_next_match()

    def jump_prev_match(self) -> None:
        self._main.jump_prev_match()

    # ---- details control ----

    def show_details(
        self, title: str, lines: list[str], meta: dict | None = None
    ) -> None:
        self.details_meta = meta or {}  # <- keep meta for key actions
        body = [title] + _make_rows(lines)
        self._details.update_list(body)
        self._details.remove_class("hidden")
        self._details_active = True
        self._details.focus()

    def hide_details(self) -> None:
        self.details_meta = {}  # clear meta on close
        if not self._details.has_class("hidden"):
            self._details_active = False
            self._details.add_class("hidden")
            self._main.focus()

    def has_details_open(self) -> bool:
        return not self._details.has_class("hidden")

    def focus_main(self) -> None:
        self._main.focus()

    def set_meta_map(self, meta_map: dict[str, dict]) -> None:
        self._meta_map = meta_map

    def get_meta_for_tag(self, tag: str) -> dict | None:
        return self._meta_map.get(tag)

    def set_detail_key_handler(self, handler: callable) -> None:
        """handler(key: str, meta: dict) -> None"""
        self._detail_key_handler = handler

    def on_key(self, event) -> None:
        """Only handle detail commands; let lowercase tag keys bubble up."""
        if not self.has_details_open():
            return

        k = event.key or ""

        # 1) Let lowercase a–z pass through (tag selection)
        if len(k) == 1 and "a" <= k <= "z":
            # do NOT stop the event; DynamicViewApp will collect the tag chars
            return

        # 2) Close details with Escape (but not 'q')
        if k == "escape":
            if self.has_details_open():
                self.hide_details()
            event.stop()
            return

        # 3) Route only your command keys to the injected handler
        if not self._detail_key_handler:
            return

        # Normalize keys: we want uppercase single-letter commands + 'ctrl+r'
        if k == "ctrl+r":
            cmd = "CTRL+R"
        elif len(k) == 1:
            cmd = k.upper()
        else:
            cmd = k  # leave other keys as-is (unlikely used)

        # Allow only the detail commands you use (uppercase)
        ALLOWED = {"E", "D", "F", "P", "N", "R", "T", "CTRL+R"}
        if cmd in ALLOWED:
            try:
                self._detail_key_handler(cmd, self.details_meta or {})
            finally:
                event.stop()


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


class DatetimePrompt(ModalScreen[datetime | None]):
    """
    Prompt for a datetime, live-parsed with dateutil.parser.parse.
    """

    def __init__(
        self,
        message: str,  # top custom lines before fixed footer
        subject: str | None = None,
        due: str | None = None,
        default: datetime | None = None,
    ):
        super().__init__()
        self.title_text = " Datetime Entry"
        self.message = message.strip()
        # self.subject = subject
        # self.due = due
        self.default = default or datetime.now()

        # assigned later
        self.input: Input | None = None
        self.feedback: Static | None = None
        self.instructions: Static | None = None

    def compose(self) -> ComposeResult:
        """Build prompt layout."""
        # ARROW = "↳"
        default_str = self.default.strftime("%Y-%m-%d %H:%M")

        def rule():
            return Static("─" * 60, classes="dim-rule")

        with Vertical(id="dt_prompt"):
            instructions = [
                "Modify the datetime belew if necessary, then press",
                "[bold yellow]ENTER[/bold yellow] to submit or [bold yellow]ESC[/bold yellow] to cancel.",
            ]
            self.instructions = Static("\n".join(instructions), id="dt_instructions")
            self.feedback = Static(f"️↳ {default_str}", id="dt_feedback")
            self.input = Input(value=default_str, id="dt_entry")
            #
            # Title
            yield Static(self.title_text, classes="title-class", id="dt_title")
            # yield rule()

            # Message (custom, may include subject/due or other contextual info)
            if self.message:
                yield Static(self.message.strip(), id="dt_message")
                # yield rule()

            yield self.instructions

            yield self.input

            yield self.feedback

            # yield rule()

    def on_mount(self) -> None:
        """Focus the input and show feedback for the initial value."""
        self.query_one("#dt_entry", Input).focus()
        self._update_feedback(self.input.value)

    # def on_input_changed(self, event: Input.Changed) -> None:
    #     """Live update feedback as user types."""
    #     self._update_feedback(event.value)

    def _update_feedback(self, text: str) -> None:
        try:
            parsed = parse(text)
            if isinstance(parsed, date) and not isinstance(parsed, datetime):
                self.feedback.update(f"datetime: {parsed.strftime('%Y-%m-%d')}")
            else:
                self.feedback.update(f"datetime: {parsed.strftime('%Y-%m-%d %H:%M')}")
        except Exception:
            _t = f": {text} " if text else ""
            self.feedback.update(f"[{ORANGE_RED}] invalid{_t}[/{ORANGE_RED}] ")

    def on_key(self, event) -> None:
        """Handle Enter and Escape."""
        if event.key == "escape":
            self.dismiss(None)
        elif event.key == "enter":
            try:
                value = self.input.value.strip()
                parsed = parse(value) if value else self.default
                self.dismiss(parsed)
            except Exception:
                self.dismiss(None)


ORANGE_RED = "red3"
FOOTER = "yellow"


class EditorScreen(Screen):
    """
    Single-Item editor with live, token-aware feedback.

    Behavior:
      - Keeps one Item instance (self.item).
      - On text change: item.final = False; item.parse_input(text)
      - Feedback shows status for the token under the cursor (if any).
      - Save / Commit:
          item.final = True; item.parse_input(text)  # finalize rrules/jobs/etc
          persist only if parse_ok, else warn.
    """

    # BINDINGS = [
    #     ("shift+enter", "commit", "Commit"),
    #     ("ctrl+s", "save", "Save"),
    #     ("escape", "close", "Back"),
    # ]
    BINDINGS = [
        ("ctrl+s", "save_and_close", "Save"),
        ("shift+enter", "save_and_close", "Commit"),
        ("escape", "close", "Back"),
    ]

    def __init__(
        self, controller, record_id: int | None = None, *, seed_text: str = ""
    ):
        super().__init__()
        self.controller = controller
        self.record_id = record_id
        self.entry_text = seed_text

        # one persistent Item
        from tklr.item import Item  # adjust import to your layout if needed

        self.ItemCls = Item
        self.item = self.ItemCls(
            seed_text, controller=self.controller
        )  # initialize with existing text
        self._feedback_lines: list[str] = []

        # widgets
        self._title: Static | None = None
        self._message: Static | None = None
        self._text: TextArea | None = None
        self._feedback: Static | None = None
        self._instructions: Static | None = None

    # ---------- Layout like DatetimePrompt ----------
    def compose(self) -> ComposeResult:
        # title_text = " Editor"
        title_text = self._build_context()

        with Vertical(id="ed_prompt"):
            instructions = [
                "Edit the entry below as desired, then press",
                f"[bold {FOOTER}]Ctrl+S[/bold {FOOTER}] to save or [bold {FOOTER}]Esc[/bold {FOOTER}] to cancel",
            ]
            self._instructions = Static("\n".join(instructions), id="ed_instructions")
            self._feedback = Static("", id="ed_feedback")
            self._text = TextArea(self.entry_text, id="ed_entry")

            yield Static(title_text, classes="title-class", id="ed_title")

            # yield Static(ctx_line, id="ed_message")

            yield self._instructions
            yield self._text
            yield self._feedback

    def on_mount(self) -> None:
        # focus editor and run initial parse (non-final)
        if self._text:
            self._text.focus()
            self._render_feedback()
        self._live_parse_and_feedback(final=False)

    # ---------- Text change -> live parse ----------
    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Re-parse using the actual TextArea content, not the event payload."""
        # Make sure we have a handle to the TextArea
        # if not getattr(self, "_text", None):
        #     self._text = self.query_one("#ed_entry", TextArea)

        # Source of truth: the widget's text property
        self.entry_text = self._text.text or ""
        self._live_parse_and_feedback(final=False)

        # Optional: stop propagation so nothing else double-handles it
        event.stop()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        # Don't re-parse—just re-render feedback for the new caret position
        self._render_feedback()

    # ---------- Actions ----------
    # def action_close(self) -> None:
    #     self.app.pop_screen()
    #
    # def action_save(self) -> None:
    #     """Finalize, re-parse, and persist if valid (no partial saves)."""
    #     ok = self._finalize_and_validate()
    #     if not ok:
    #         self.app.notify("Cannot save: fix errors first.", severity="warning")
    #         return
    #     self._persist(self.item)
    #     self.app.notify("Saved.", timeout=1.0)
    #
    #
    # def action_commit(self) -> None:
    #     """Same semantics as save; you can keep separate if you want a different UX."""
    #     ok = self._finalize_and_validate()
    #     if not ok:
    #         self.app.notify("Cannot commit: fix errors first.", severity="warning")
    #         return
    #     self._persist(self.item)
    #     self.app.notify("Committed.", timeout=1.0)
    #     self._try_refresh_calling_view()
    #     self.app.pop_screen()

    def action_save_and_close(self) -> None:
        ok = self._finalize_and_validate()
        if not ok:
            self.app.notify("Cannot save: fix errors first.", severity="warning")
            return
        self._persist(self.item)
        self.app.notify("Saved.", timeout=0.8)
        self.dismiss({"changed": True, "record_id": self.record_id})

    # def action_save(self) -> None:        # optional shim
    #     self.action_save_and_close()
    #
    # def action_commit(self) -> None:      # optional shim
    #     self.action_save_and_close()

    def action_close(self) -> None:
        self.dismiss(None)  # close without saving

    # ---------- Internals ----------
    def _build_context(self) -> str:
        if self.record_id is None:
            return "New item"
        row = self.controller.db_manager.get_record(self.record_id)
        # subj = row[2] or "(untitled)"
        return f"Editing Record {self.record_id}"

    def _finalize_and_validate(self) -> bool:
        """
        Finalize the entry (rrules/jobs/etc) and validate.
        Returns True iff parse_ok after a finalizing parse.
        """
        if not getattr(self.item, "parse_ok", False):
            self._render_feedback()
            return False

        self.item.final = True
        self.item.parse_input(self.entry_text)
        self.item.finalize_record()
        return self.item.parse_ok

    def _live_parse_and_feedback(self, *, final: bool) -> None:
        """Non-throwing live parse + feedback for current cursor token."""
        self.item.final = bool(final)
        self.item.parse_input(self.entry_text)
        self._render_feedback()

    def _token_at(self, idx: int) -> Optional[Dict[str, Any]]:
        """Find the token whose [s,e) spans idx; fallback to first incomplete after idx."""
        toks: List[Dict[str, Any]] = getattr(self.item, "relative_tokens", []) or []
        for t in toks:
            s, e = t.get("s", -1), t.get("e", -1)
            if s <= idx < e:
                return t
        for t in toks:
            if t.get("incomplete") and t.get("s", 1 << 30) >= idx:
                return t
        return None

    def _cursor_abs_index(self) -> int:
        """Map TextArea (row, col) to absolute index in self.entry_text."""
        try:
            ta = self.query_one("#ed_entry", TextArea)
        except NoMatches:
            return len(self.entry_text or "")
        loc = getattr(ta, "cursor_location", None)
        if not loc:
            return len(self.entry_text or "")
        row, col = loc
        lines = (self.entry_text or "").splitlines(True)  # keep \n
        if row >= len(lines):
            return len(self.entry_text or "")
        return sum(len(l) for l in lines[:row]) + min(col, len(lines[row]))

    def _render_feedback(self) -> None:
        """Update the feedback panel using only screen state."""
        _AT_DESC = {
            "#": "Ref / id",
            "+": "Include datetimes",
            "-": "Exclued datetimes",
            "a": "Alert",
            "b": "Bin",
            "c": "Context",
            "d": "Description",
            "e": "Extent",
            "g": "Goal",
            "k": "Keyword",
            "l": "Location",
            "m": "Mask",
            "n": "Notice",
            "o": "Offset",
            "p": "Priority 1 - 5 (low - high)",
            "r": "Repetition frequency",
            "s": "Scheduled datetime",
            "t": "Tags",
            "u": "URL",
            "w": "Wrap",
            "x": "Exclude dates",
            "z": "Timezone",
        }
        _AMP_DESC = {
            "r": "Repetiton frequency",
            "c": "Count",
            "d": "By month day",
            "m": "By month",
            "H": "By hour",
            "M": "By minute",
            "E": "By-second",
            "i": "Interval",
            "s": "Schedule offset",
            "u": "Until",
            "W": "ISO week",
            "w": "Weekday modifier",
        }

        log_msg(f"{self.entry_text = }, {self._text.text = }")
        panel = self.query_one("#ed_feedback", Static)  # <— direct, no fallback

        item = getattr(self, "item", None)
        log_msg(f"{item = }")
        if not item:
            panel.update("")
            return

        # 1) Show validate messages if any.
        if self.item.validate_messages:
            log_msg(f"{self.item.validate_messages = }")
            panel.update("\n".join(self.item.validate_messages))
            return

        msgs = getattr(item, "messages", None) or []
        log_msg(f"{msgs = }")
        if msgs:
            l = []
            if isinstance(msgs, list):
                for msg in msgs:
                    if isinstance(msg, tuple):
                        l.append(msg[1])
                    else:
                        l.append(msg)

            s = "\n".join(l)
            log_msg(f"{s = }")
            # panel.update("\n".join(msgs))
            panel.update(s)
            return

        last = getattr(item, "last_result", None)
        log_msg(f"{last = }")
        if last and last[1]:
            panel.update(str(last[1]))
            # return

        # 2) No errors: describe token at cursor (with normalized preview if available).
        idx = self._cursor_abs_index()
        tok = self._token_at(idx)
        log_msg(f"{idx = } {tok = }")

        if not tok:
            # panel.update("")
            return

        ttype = tok.get("t", "")
        raw = tok.get("token", "").strip()
        log_msg(f"{raw = }")
        k = tok.get("k", "")

        preview = ""
        last = getattr(item, "last_result", None)
        log_msg(f"{last = }")
        # if isinstance(last, tuple) and len(last) >= 3 and last[0] is True:
        if isinstance(last, tuple) and len(last) >= 3:
            meta = last[2] or {}
            if meta.get("s") == tok.get("s") and meta.get("e") == tok.get("e"):
                norm_val = last[1]
                if isinstance(norm_val, str) and norm_val:
                    preview = f"{meta.get('t')}{meta.get('k')} {norm_val}"

        if ttype == "itemtype":
            panel.update(f"itemtype: {self.item.itemtype}")
        elif ttype == "subject":
            panel.update(f"subject: {self.item.subject}")
        elif ttype == "@":
            # panel.update(f"↳ @{k or '?'} {preview or raw}")
            key = tok.get("k", None)
            description = f"{_AT_DESC.get(key, '')}:" if key else "↳"
            panel.update(f"{description} {preview or raw}")
        elif ttype == "&":
            key = tok.get("k", None)
            description = f"{_AMP_DESC.get(key, '')}:" if key else "↳"
            panel.update(f"{description} {preview or raw}")
        else:
            panel.update(f"↳ {raw}{preview}")

    # def _persist(self, item) -> None:
    #     """Create or update the DB row using your model layer; only called when parse_ok is True."""
    #     if self.record_id is None:
    #         rid = self.controller.db_manager.add_item(item)  # uses full item fields
    #         self.record_id = rid
    #     else:
    #         self.controller.db_manager.update_item(self.record_id, item)

    def _persist(self, item) -> None:
        rid = self.controller.db_manager.save_record(item, record_id=self.record_id)
        self.record_id = rid

    # def _try_refresh_calling_view(self) -> None:
    #     for scr in getattr(self.app, "screen_stack", []):
    #         if hasattr(scr, "refresh_data"):
    #             try:
    #                 scr.refresh_data()
    #             except Exception:
    #                 pass


class DetailsScreen(ModalScreen[None]):
    BINDINGS = [
        ("escape", "close", "Back"),
        ("?", "show_help", "Help"),
        ("ctrl+q", "quit", "Quit"),
        ("alt+e", "edit_item", "Edit"),
        ("alt+c", "copy_item", "Copy"),
        ("alt+d", "delete_item", "Delete"),
        ("alt+f", "finish_task", "Finish"),  # tasks only
        ("alt+p", "toggle_pinned", "Pin/Unpin"),  # tasks only
        ("alt+n", "schedule_new", "Schedule"),
        ("alt+r", "reschedule", "Reschedule"),
        ("alt+t", "touch_item", "Touch"),
        ("ctrl+r", "show_repetitions", "Show Repetitions"),
    ]

    # Actions mapped to bindings
    def action_edit_item(self) -> None:
        self._edit_item()

    def action_copy_item(self) -> None:
        self._copy_item()

    def action_delete_item(self) -> None:
        self._delete_item()

    def action_finish_task(self) -> None:
        if self.is_task:
            self._finish_task()

    def action_toggle_pinned(self) -> None:
        if self.is_task:
            self._toggle_pinned()

    def action_schedule_new(self) -> None:
        self._schedule_new()

    def action_reschedule(self) -> None:
        self._reschedule()

    def action_touch_item(self) -> None:
        self._touch_item()

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
        self.set_focus(self)  # 👈 this makes sure the modal is active for bindings
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

    def action_show_repetitions(self) -> None:
        if self.is_recurring:
            self._show_repetitions()

    # def action_show_help(self) -> None:
    #     self.app.push_screen(DetailsHelpScreen(self._build_help_text()))

    def action_show_help(self) -> None:
        # Build the specialized details help
        lines = self._build_help_text().splitlines()
        self.app.push_screen(HelpScreen(lines))

    # ---------- wire these to your controller ----------
    def _edit_item(self) -> None:
        # e.g. self.app.controller.edit_record(self.record_id)
        log_msg("edit_item")

    def _copy_item(self) -> None:
        # e.g. self.app.controller.copy_record(self.record_id)
        log_msg("copy_item")

    def _delete_item(self) -> None:
        # e.g. self.app.controller.delete_record(self.record_id, scope=...)
        log_msg("delete_item")

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
        log_msg("finish_task")
        return

        meta = self.app.controller.get_last_details_meta() or {}
        record_id = meta.get("record_id")
        job_id = meta.get("job_id")  # may be None for non-project tasks

        if not record_id:
            self.app.notify("No record selected.")
            return

        # dt = datetime.now()
        dt = self._prompt_finish_datetime()
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
        log_msg("toggle_pin")
        return

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
        log_msg("schedule_new")

    def _reschedule(self) -> None:
        # e.g. self.app.controller.reschedule(self.record_id)
        log_msg("reschedule")

    def _touch_item(self) -> None:
        # e.g. self.app.controller.touch_record(self.record_id)
        log_msg("touch")

    def _show_repetitions(self) -> None:
        log_msg("show_repetitions")
        if not self.is_recurring or self.record_id is None:
            return
        # e.g. rows = self.app.controller.list_repetitions(self.record_id)
        pass

    def _show_completions(self) -> None:
        log_msg("show_completions")
        if not self.is_task or self.record_id is None:
            return
        # e.g. rows = self.app.controller.list_completions(self.record_id)
        pass


class HelpScreen(Screen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]

    def __init__(self, lines: list[str], footer: str = ""):
        super().__init__()
        self._title = lines[0]
        self._lines = lines[1:]
        self._footer = footer or f"[bold {FOOTER}]esc[/bold {FOOTER}] Back"
        self.add_class("panel-bg-help")  # HelpScreen

    def compose(self):
        yield Vertical(
            Static(self._title, id="details_title", classes="title-class"),
            ScrollableList(self._lines, id="help_list"),
            Static(self._footer, id="custom_footer"),
            id="help_layout",
        )

    def on_mount(self):
        self.styles.width = "100%"
        self.styles.height = "100%"
        self.query_one("#help_layout").styles.height = "100%"

        help_list = self.query_one("#help_list", ScrollableList)
        for attr in ("_viewport", "_window", "_scroll_view", "_view", "_content"):
            vp = getattr(help_list, attr, None)
            if vp and hasattr(vp, "styles"):
                vp.styles.background = "#373737"
                try:
                    vp.refresh()
                except Exception:
                    pass
        log_msg(
            f"help_layout children: {[(i, child.__class__.__name__, child.id, child.styles.background) for i, child in enumerate(self.query_one('#help_layout').children)]}"
        )  # Make sure it fills the screen; no popup sizing/margins.


class ScrollableList(ScrollView):
    """A scrollable list widget with title-friendly rendering and search.

    Features:
      - Efficient virtualized rendering (line-by-line).
      - Simple search with highlight.
      - Jump to next/previous match.
      - Easy list updating via `update_list`.
    """

    DEFAULT_CSS = """
    ScrollableList {
        background: #373737 90%;
    }
    """

    def __init__(self, lines: List[str], *, match_color: str = MATCH_COLOR, **kwargs):
        super().__init__(**kwargs)
        self.console = Console()
        self.match_color = match_color
        self.row_bg = Style(bgcolor="#373737")  # ← row background color

        self.lines: List[Text] = [Text.from_markup(line) for line in lines]
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))

        self.search_term: Optional[str] = None
        self.matches: List[int] = []
        self.current_match_idx: int = -1

    # ... update_list / search methods unchanged ...

    def update_list(self, new_lines: List[str]) -> None:
        """Replace the list content and refresh."""
        # log_msg(f"{new_lines = }")
        self.lines = [Text.from_markup(line) for line in new_lines if line]
        # log_msg(f"{self.lines = }")
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

    def render_line(self, y: int) -> Strip:
        """Render a single virtual line at viewport row y with full-row background."""
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y

        if y < 0 or y >= len(self.lines):
            # pad a blank row with background so empty area is painted too
            return Strip(
                Segment.adjust_line_length([], self.size.width, style=self.row_bg),
                self.size.width,
            )

        # copy so we can stylize safely
        line_text = self.lines[y].copy()

        # search highlight (doesn't touch background)
        if self.search_term and y in self.matches:
            line_text.stylize(f"bold {self.match_color}")

        # ensure everything drawn has background
        line_text.stylize(self.row_bg)

        # render → crop/pad to width; pad uses our background style
        segments = list(line_text.render(self.console))
        segments = Segment.adjust_line_length(
            segments, self.size.width, style=self.row_bg
        )

        return Strip(segments, self.size.width)


class SearchableScreen(Screen):
    """Base class for screens that support search on a list widget."""

    def get_search_target(self):
        """Return the ScrollableList that should receive search/scroll commands.

        If details pane is open, target the details list, otherwise the main list.
        """
        if not self.list_with_details:
            return None

        # if details is open, search/scroll that; otherwise main list
        return (
            self.list_with_details._details
            if self.list_with_details.has_details_open()
            else self.list_with_details._main
        )

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

    def get_search_term(self) -> str:
        """
        Return the current search string for this screen.

        Priority:
          1. If the screen exposes a search input widget (self.search_input),
             return its current value (.value or .text).
          2. If this screen wants to store the term elsewhere, override this method.
          3. Fallback to the app-wide reactive `self.app.search_term`.
        """
        # 1) common pattern: a Textual Input-like widget called `search_input`
        si = getattr(self, "search_input", None)
        if si is not None:
            # support common widget APIs
            if hasattr(si, "value"):
                return si.value or ""
            if hasattr(si, "text"):
                return si.text or ""
            # fallback convert to str
            try:
                return str(si)
            except Exception:
                return ""

        # 2) some screens may keep the term on the screen in another attribute;
        #    override get_search_term in those screens if needed.

        # 3) fallback app-wide value
        return getattr(self.app, "search_term", "") or ""


# type aliases for clarity
PageRows = List[str]
PageTagMap = Dict[str, Tuple[int, Optional[int]]]  # tag -> (record_id, job_id|None)
Page = Tuple[PageRows, PageTagMap]


class WeeksScreen(SearchableScreen, SafeScreen):
    """
    1-week grid with a bottom details panel, powered by ListWithDetails.

    `details` is expected to be a list of pages:
      pages = [ (rows_for_page0, tag_map0), (rows_for_page1, tag_map1), ... ]
    where rows_for_pageX is a list[str] (includes header rows and record rows)
    and tag_mapX maps single-letter tags 'a'..'z' to (record_id, job_id|None).
    """

    def __init__(
        self,
        title: str,
        table: str,
        details: Optional[List[Page]],
        footer_content: str,
    ):
        super().__init__()
        log_msg(f"{self.app = }, {self.app.controller = }")
        self.add_class("panel-bg-weeks")  # WeeksScreen
        self.table_title = title
        self.table = table  # busy bar / calendar mini-grid content (string)
        # pages: list of (rows, tag_map). Accept None or [].
        self.pages: List[Page] = details or []
        self.current_page: int = 0

        # footer string (unchanged)
        self.footer_content = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.list_with_details: Optional[ListWithDetails] = None

    # Let global search target the currently-focused list
    def get_search_target(self):
        if not self.list_with_details:
            return None
        return (
            self.list_with_details._details
            if self.list_with_details.has_details_open()
            else self.list_with_details._main
        )

    # --- Compose/layout -------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(
            self.table_title or "Untitled",
            id="table_title",
            classes="title-class",
        )

        yield Static(
            self.table or "[i]No data[/i]",
            id="table",
            classes="busy-bar",
            markup=True,
        )

        # Single list (no separate list title)
        self.list_with_details = ListWithDetails(id="list")
        # keep the same handler wiring as before (detail opens a record details)
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(
                view_name="weeks",
                week_provider=lambda: self.app.selected_week,
            )
        )
        self.app.detail_handler = self.list_with_details._detail_key_handler
        yield self.list_with_details

        yield Static(self.footer_content, id="custom_footer")

    # Called once layout is up
    def after_mount(self) -> None:
        """Populate the list with the current page once layout is ready."""
        if self.list_with_details:
            self.refresh_page()

    # --- Page management API (used by DynamicViewApp) -------------------
    def has_next_page(self) -> bool:
        return self.current_page < (len(self.pages) - 1)

    def has_prev_page(self) -> bool:
        return self.current_page > 0

    def next_page(self) -> None:
        if self.has_next_page():
            self.current_page += 1
            self.refresh_page()

    def previous_page(self) -> None:
        if self.has_prev_page():
            self.current_page -= 1
            self.refresh_page()

    def reset_to_first_page(self) -> None:
        if self.pages:
            self.current_page = 0
            self.refresh_page()

    def get_record_for_tag(self, tag: str) -> Optional[Tuple[int, Optional[int]]]:
        """Return (record_id, job_id) for a tag on the current page or None."""
        if not self.pages:
            return None
        _, tag_map = self.pages[self.current_page]
        return tag_map.get(tag)

    # --- UI refresh helpers ---------------------------------------------

    def refresh_page(self) -> None:
        """Update the ListWithDetails widget to reflect the current page (with debug)."""
        log_msg(
            f"[WeeksScreen.refresh_page] current_page={self.current_page}, total_pages={len(self.pages)}"
        )
        if not self.list_with_details:
            log_msg("[WeeksScreen.refresh_page] no list_with_details widget")
            return

        if not self.pages:
            log_msg("[WeeksScreen.refresh_page] no pages -> clearing list")
            self.list_with_details.update_list([])
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()
            # ensure controller expects single-letter tags for weeks
            self.app.controller.afill_by_view["weeks"] = 1
            # ensure title shows base title (no indicator)
            self.query_one("#table_title", Static).update(self.table_title)
            return

        # defensive: check page index bounds
        if self.current_page < 0 or self.current_page >= len(self.pages):
            log_msg(
                f"[WeeksScreen.refresh_page] current_page out of bounds, resetting to 0"
            )
            self.current_page = 0

        page = self.pages[self.current_page]
        # validate page tuple shape
        if not (isinstance(page, (list, tuple)) and len(page) == 2):
            log_msg(
                f"[WeeksScreen.refresh_page] BAD PAGE SHAPE at index {self.current_page}: {type(page)} {page!r}"
            )
            # try to fall back: if pages is a list of rows (no tag maps), display as-is
            if isinstance(self.pages, list) and all(
                isinstance(p, str) for p in self.pages
            ):
                self.list_with_details.update_list(self.pages)
                # update title without indicator
                self.query_one("#table_title", Static).update(self.table_title)
                return
            # otherwise clear to avoid crash
            self.list_with_details.update_list([])
            self.query_one("#table_title", Static).update(self.table_title)
            return

        rows, tag_map = page
        log_msg(
            f"[WeeksScreen.refresh_page] page {self.current_page} rows={len(rows)} tags={len(tag_map)}"
        )
        # update list contents
        self.list_with_details.update_list(rows)
        # reset controller afill for week -> single-letter tags (page_tagger guarantees this)
        self.app.controller.afill_by_view["weeks"] = 1

        if self.list_with_details.has_details_open():
            # close stale details when page changes (optional)
            self.list_with_details.hide_details()

        # --- update table title to include page indicator when needed ---
        if len(self.pages) > 1:
            indicator = f" ({self.current_page + 1}/{len(self.pages)})"
        else:
            indicator = ""
        self.query_one("#table_title", Static).update(f"{self.table_title}{indicator}")

    # --- Called from app when the underlying week data has changed ----------

    def update_table_and_list(self):
        """
        Called by app after the controller recomputes the table + list pages
        for the currently-selected week.
        Controller.get_table_and_list must now return: (title, busy_bar, pages)
        where pages is a list[Page].
        """
        title, busy_bar, pages = self.app.controller.get_table_and_list(
            self.app.current_start_date, self.app.selected_week
        )

        log_msg(
            f"[WeeksScreen.update_table_and_list] controller returned title={title!r} busy_bar_len={len(busy_bar) if busy_bar else 0} pages_type={type(pages)}"
        )

        # some controllers might mistakenly return (pages, header) tuple; normalize:
        normalized_pages = pages
        # If it's a tuple (pages, header) — detect and unwrap
        if isinstance(pages, tuple) and len(pages) == 2 and isinstance(pages[0], list):
            log_msg(
                "[WeeksScreen.update_table_and_list] Detected (pages, header) tuple; unwrapping first element as pages."
            )
            normalized_pages = pages[0]

        # final validation: normalized_pages should be list of (rows, tag_map)
        if not isinstance(normalized_pages, list):
            log_msg(
                f"[WeeksScreen.update_table_and_list] WARNING: pages is not a list: {type(normalized_pages)} -> treating as empty"
            )
            normalized_pages = []

        # optionally, do a quick contents-sanity check
        page_cnt = len(normalized_pages)
        sample_info = []
        for i, p in enumerate(normalized_pages[:3]):
            if isinstance(p, (list, tuple)) and len(p) == 2:
                sample_info.append((i, len(p[0]), len(p[1])))
            else:
                sample_info.append((i, "BAD_PAGE_SHAPE", type(p)))
        log_msg(
            f"[WeeksScreen.update_table_and_list] pages_count={page_cnt} sample={sample_info}"
        )

        # adopt new pages and reset page index
        self.pages = normalized_pages
        self.current_page = 0

        # Save base title so refresh_page can add indicator consistently
        self.table_title = title

        # update busy-bar immediately
        self.query_one("#table", Static).update(busy_bar)

        # update the title now including an indicator if appropriate
        if len(self.pages) > 1:
            title_with_indicator = (
                f"{self.table_title}\n({self.current_page + 1}/{len(self.pages)})"
            )
        else:
            title_with_indicator = self.table_title
        self.query_one("#table_title", Static).update(title_with_indicator)

        # refresh the visible page (calls update_list and will also update title)
        if self.list_with_details:
            self.refresh_page()

    # --- Tag activation -> show details ----------------------------------
    def show_details_for_tag(self, tag: str) -> None:
        """
        Called by DynamicViewApp when a tag is completed.
        We look up the record_id/job_id for this tag on the current page and then
        ask the controller for details and show them in the lower panel.
        """
        rec = self.get_record_for_tag(tag)
        if not rec:
            return
        record_id, job_id = rec

        # Controller helper returns title, list-of-lines (fields), and meta
        title, lines, meta = self.app.controller.get_details_for_record(
            record_id, job_id
        )
        if self.list_with_details:
            self.list_with_details.show_details(title, lines, meta)


class FullScreenList(SearchableScreen):
    """Full-screen list view with paged navigation and tag support."""

    def __init__(self, pages, title, header="", footer_content="..."):
        super().__init__()
        self.pages = pages  # list of (rows, tag_map)
        self.title = title
        self.header = header
        self.footer_content = footer_content
        # self.footer_content = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.current_page = 0
        self.lines = []
        self.tag_map = {}
        if self.pages:
            self.lines, self.tag_map = self.pages[0]
        self.list_with_details: ListWithDetails | None = None
        self.add_class("panel-bg-list")  # FullScreenList

    # --- Page Navigation ----------------------------------------------------
    def next_page(self):
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self.refresh_list()

    def previous_page(self):
        if self.current_page > 0:
            self.current_page -= 1
            self.refresh_list()

    # --- Tag Lookup ---------------------------------------------------------
    def get_record_for_tag(self, tag: str):
        """Return the record_id corresponding to a tag on the current page."""
        _, tag_map = self.pages[self.current_page]
        return tag_map.get(tag)

    def show_details_for_tag(self, tag: str) -> None:
        app = self.app  # DynamicViewApp
        record = self.get_record_for_tag(tag)
        if record:
            record_id, job_id = record

            title, lines, meta = app.controller.get_details_for_record(
                record_id, job_id
            )
            log_msg(f"{title = }, {lines = }, {meta = }")
            if self.list_with_details:
                self.list_with_details.show_details(title, lines, meta)

    def _render_page_indicator(self) -> str:
        total_pages = len(self.pages)
        if total_pages <= 1:
            return ""
        return f" ({self.current_page + 1}/{total_pages})"

    # --- Refresh Display ----------------------------------------------------
    def refresh_list(self):
        page_rows, tag_map = self.pages[self.current_page]
        self.lines = page_rows
        self.tag_map = tag_map
        if self.list_with_details:
            self.list_with_details.update_list(self.lines)
        # Update header/title with bullet indicator
        header_text = f"{self.title}{self._render_page_indicator()}"
        self.query_one("#scroll_title", Static).update(header_text)

    # --- Compose ------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Static(self.title, id="scroll_title", expand=True, classes="title-class")
        if self.header:
            yield Static(
                self.header, id="scroll_header", expand=True, classes="header-class"
            )
        self.list_with_details = ListWithDetails(id="list")
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(view_name="next")
        )
        yield self.list_with_details
        yield Static(self.footer_content, id="custom_footer")

    def on_mount(self) -> None:
        if self.list_with_details:
            self.list_with_details.update_list(self.lines)
        # Add the initial page indicator after mount
        self.query_one("#scroll_title", Static).update(
            f"{self.title}{self._render_page_indicator()}"
        )


Page = Tuple[List[str], Dict[str, Tuple[str, object]]]

# Reuse your ListWithDetails and SearchableScreen base
# from .view import ListWithDetails, SearchableScreen, FOOTER  (adjust import as appropriate)


# class BinView(SearchableScreen):
#     """Single Bin browser with paged tags and a details panel."""
#
#     def __init__(self, controller, bin_id: int, footer_content: str = ""):
#         super().__init__()
#         self.controller = controller
#         self.bin_id = bin_id
#         self.pages = []  # list[Page] = [(rows, tag_map), ...]
#         self.current_page = 0
#         self.title = ""
#         self.footer_content = (
#             footer_content
#             or f"[bold {FOOTER}]←/→[/bold {FOOTER}] Page  [bold {FOOTER}]ESC[/bold {FOOTER}] Root  [bold {FOOTER}]/[/bold {FOOTER}] Search"
#         )
#         self.list_with_details = None
#         self.tag_map = {}
#
#     # ----- Compose -----
#     def compose(self) -> ComposeResult:
#         yield Static("", id="scroll_title", classes="title-class", expand=True)
#         self.list_with_details = ListWithDetails(id="list")
#         # Details handler is the same as other views (uses controller.get_details_for_record)
#         self.list_with_details.set_detail_key_handler(
#             self.app.make_detail_key_handler(view_name="bin")
#         )
#         yield self.list_with_details
#         yield Static(self.footer_content, id="custom_footer")
#
#     # ----- Lifecycle -----
#     def on_mount(self):
#         self.refresh_bin()
#
#     # ----- Public mini-API (called by app’s on_key) -----
#     def next_page(self):
#         if self.current_page < len(self.pages) - 1:
#             self.current_page += 1
#             self._refresh_page()
#
#     def previous_page(self):
#         if self.current_page > 0:
#             self.current_page -= 1
#             self._refresh_page()
#
#     def has_next_page(self) -> bool:
#         return self.current_page < len(self.pages) - 1
#
#     def has_prev_page(self) -> bool:
#         return self.current_page > 0
#
#     def show_details_for_tag(self, tag: str) -> None:
#         """Called by DynamicViewApp for tag keys a–z."""
#         if not self.pages:
#             return
#         _, tag_map = self.pages[self.current_page]
#         payload = tag_map.get(tag)
#         if not payload:
#             return
#
#         kind, data = payload
#         if kind == "bin":
#             # navigate into that bin
#             self.bin_id = int(data)
#             self.refresh_bin()
#             return
#
#         # record -> open details
#         record_id, job_id = data
#         title, lines, meta = self.controller.get_details_for_record(record_id, job_id)
#         if self.list_with_details:
#             self.list_with_details.show_details(title, lines, meta)
#
#     # ----- Local key handling -----
#     def on_key(self, event):
#         k = event.key
#         if k == "escape":
#             # Jump to root
#             root_id = getattr(self.controller, "root_id", None)
#             if root_id is not None:
#                 self.bin_id = root_id
#                 self.refresh_bin()
#                 event.stop()
#                 return
#
#         if k == "left":
#             if self.has_prev_page():
#                 self.previous_page()
#                 event.stop()
#         elif k == "right":
#             if self.has_next_page():
#                 self.next_page()
#                 event.stop()
#
#     # ----- Internal helpers -----
#     def refresh_bin(self):
#         self.pages, self.title = self.controller.get_bin_pages(self.bin_id)
#         self.current_page = 0
#         self._refresh_page()
#
#     def _refresh_page(self):
#         rows, tag_map = self.pages[self.current_page] if self.pages else ([], {})
#         self.tag_map = tag_map
#         if self.list_with_details:
#             self.list_with_details.update_list(rows)
#             if self.list_with_details.has_details_open():
#                 self.list_with_details.hide_details()
#         self._refresh_header()
#
#     def _refresh_header(self):
#         bullets = self._page_bullets()
#         self.query_one("#scroll_title", Static).update(
#             f"{self.title} ({bullets})" if bullets else f"{self.title}"
#         )
#
#     def _page_bullets(self) -> str:
#         n = len(self.pages)
#         if n <= 1:
#             return ""
#         # return " ".join("●" if i == self.current_page else "○" for i in range(n))
#         return f"{self.current_page + 1}/{n}"


###VVV new for tagged bin screen
# --- Row types expected from the controller ---
@dataclass
class ChildBinRow:
    bin_id: int
    name: str
    child_ct: int
    rem_ct: int


@dataclass
class ReminderRow:
    record_id: int
    subject: str
    itemtype: str


# --- Constants ---
TAGS = [chr(ord("a") + i) for i in range(26)]  # single-letter tags per page


class TaggedHierarchyScreen(SearchableScreen):
    """
    Tagged hierarchy browser that mirrors BinView’s behavior:

      • Uses SearchableScreen + ListWithDetails.
      • Shows the *entire subtree of bins* under the current bin (bins only; no reminders below).
      • Only the current bin's *immediate children* + its *reminders* are taggable:
          - children appear in the tree with inline tags (a..z) on depth-1 rows;
          - reminders appear at the bottom with their tags.
      • Tags are paged 26-per-page (children first, then reminders).
      • a–z tags are handled by DynamicViewApp via show_details_for_tag(), exactly like BinView.
      • / search highlights within the list.
      • Digits 0..9 jump to breadcrumb ancestors (0=root, 1=child, etc.), current bin unnumbered.
      • Left/Right change pages; ESC jumps to root.
    """

    def __init__(self, controller, bin_id: int, footer_content: str = ""):
        super().__init__()
        self.controller = controller
        self.bin_id = bin_id

        # pages: list[(rows, tag_map)], where:
        #   rows    -> list[str] rendered in ListWithDetails
        #   tag_map -> {tag: ("bin", bin_id) | ("rem", (record_id, job_id))}
        self.pages: list[tuple[list[str], dict[str, tuple[str, object]]]] = []
        self.current_page: int = 0
        self.title: str = ""
        self.footer_content = (
            footer_content
            or f"[bold {FOOTER}]?[/bold {FOOTER}] Help "
            f" [bold {FOOTER}]/[/bold {FOOTER}] Search "
        )
        self.list_with_details: Optional[ListWithDetails] = None
        self.tag_map: dict[str, tuple[str, object]] = {}
        self.crumb: list[tuple[int, str]] = []  # [(id, name), ...]
        self.descendants: list[tuple[int, str, int]] = []  # (bin_id, name, depth)

    # ----- Compose -----
    def compose(self) -> ComposeResult:
        # Title: breadcrumb + optional page indicator
        yield Static("", id="scroll_title", classes="title-class", expand=True)

        self.list_with_details = ListWithDetails(id="list")
        # Details handler is the same pattern as other views
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(view_name="bins")
        )
        yield self.list_with_details

        yield Static(self.footer_content, id="custom_footer")

    # ----- Lifecycle -----
    def on_mount(self) -> None:
        self.refresh_hierarchy()

    # ----- Public mini-API (called by app’s on_key for tags) -----
    def next_page(self) -> None:
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            self._refresh_page()

    def previous_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_page()

    def has_next_page(self) -> bool:
        return self.current_page < len(self.pages) - 1

    def has_prev_page(self) -> bool:
        return self.current_page > 0

    def show_details_for_tag(self, tag: str) -> None:
        """Called by DynamicViewApp for tag keys a–z."""
        if not self.pages:
            return
        _, tag_map = self.pages[self.current_page]
        payload = tag_map.get(tag)
        if not payload:
            return

        kind, data = payload
        if kind == "bin":
            # navigate into that bin
            self.bin_id = int(data)
            self.refresh_hierarchy()
            return

        # "rem" -> open details
        record_id, job_id = data
        title, lines, meta = self.controller.get_details_for_record(record_id, job_id)
        if self.list_with_details:
            self.list_with_details.show_details(title, lines, meta)

    # ----- Local key handling -----
    def on_key(self, event) -> None:
        k = event.key

        # ESC -> jump to root (same behavior as BinView)
        if k == "escape":
            root_id = getattr(self.controller, "root_id", None)
            if root_id is not None:
                self.bin_id = root_id
                self.refresh_hierarchy()
                event.stop()
                return

        # digits -> breadcrumb jump (ancestors only, last crumb is current bin)
        if k.isdigit():
            i = int(k)
            if 0 <= i < len(self.crumb) - 1:
                self.bin_id = self.crumb[i][0]
                self.refresh_hierarchy()
                event.stop()
                return

        # Left/Right for paging
        if k == "left":
            if self.has_prev_page():
                self.previous_page()
                event.stop()
        elif k == "right":
            if self.has_next_page():
                self.next_page()
                event.stop()
        # All other keys (including /, a–z) bubble up to SearchableScreen / app

    # ----- Internal helpers -----
    def refresh_hierarchy(self) -> None:
        """Rebuild pages and redraw from the current bin."""
        self.pages, self.title = self._build_pages_and_title()
        self.current_page = 0
        self._refresh_page()

    def _refresh_page(self) -> None:
        rows, tag_map = self.pages[self.current_page] if self.pages else ([], {})
        self.tag_map = tag_map

        if self.list_with_details:
            self.list_with_details.update_list(rows)
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()

        self._refresh_header()

    def _refresh_header(self) -> None:
        bullets = self._page_bullets()  # "1/3" or ""
        if bullets:
            header = f"Bins ({bullets})"
        else:
            header = "Bins"
        self.query_one("#scroll_title", Static).update(header)

    def _page_bullets(self) -> str:
        n = len(self.pages)
        if n <= 1:
            return ""
        return f"{self.current_page + 1}/{n}"

    def _build_pages_and_title(
        self,
    ) -> tuple[list[tuple[list[str], dict[str, tuple[str, object]]]], str]:
        """
        Build pages:
        - rows: breadcrumb line + tree (bins only) + reminders for that page
        - tag_map: tags -> ("bin", bin_id) or ("rem", (record_id, job_id))
        Returns (pages, title), where title is just the breadcrumb text (no page indicator).
        """
        # 1) Summary + breadcrumb
        children, reminders, crumb = self.controller.get_bin_summary(
            self.bin_id, filter_text=None
        )
        self.crumb = crumb

        # 2) Full subtree (bins only)
        self.descendants = self.controller.get_descendant_tree(self.bin_id)
        log_msg(f"{self.descendants = }, {children = }")

        # 3) Crumb text: ancestors numbered, last (current) unnumbered
        if crumb:
            parts: list[str] = []
            for i, (_bid, name) in enumerate(crumb):
                if i < len(crumb) - 1:
                    parts.append(
                        f"[dim]{i}[/dim] [{TYPE_TO_COLOR['b']}]{name}[/{TYPE_TO_COLOR['b']}]"
                    )
                else:
                    parts.append(
                        f"[bold {TYPE_TO_COLOR['B']}]{name}[/bold {TYPE_TO_COLOR['B']}]"
                    )
                    # parts.append(f"[bold red]{name}[/bold red]")
            crumb_txt = " / ".join(parts)
        else:
            crumb_txt = "root"

        # 4) Build taggable items: children first, then reminders
        taggable: list[tuple[str, object]] = []
        for ch in children:
            taggable.append(("bin", ch.bin_id))
        for r in reminders:
            taggable.append(("rem", (r.record_id, None)))  # job_id=None for now

        # Map reminders by ID for label rendering
        rem_by_id: dict[int, ReminderRow] = {r.record_id: r for r in reminders}

        pages: list[tuple[list[str], dict[str, tuple[str, object]]]] = []

        if not taggable:
            # No taggable items; show breadcrumb + tree as a single page
            tree_rows = self._render_tree_rows(self.descendants, child_tags={})
            rows = [crumb_txt] + tree_rows
            pages.append((rows, {}))
            return pages, crumb_txt  # title = crumb_txt

        total = len(taggable)
        num_pages = (total + 25) // 26  # 26 tags per page

        for page_index in range(num_pages):
            start = page_index * 26
            end = min(start + 26, total)
            page_items = taggable[start:end]

            page_tag_map: dict[str, tuple[str, object]] = {}
            child_tags: dict[int, str] = {}

            # Assign tags to taggable items for this page
            for i, (kind, data) in enumerate(page_items):
                tag = TAGS[i]
                if kind == "bin":
                    bin_id = int(data)
                    page_tag_map[tag] = ("bin", bin_id)
                    child_tags[bin_id] = tag
                else:  # "rem"
                    record_id, job_id = data
                    page_tag_map[tag] = ("rem", (record_id, job_id))

            # Tree rows (bins only) with inline tags on depth-1 nodes
            rows: list[str] = self._render_tree_rows(self.descendants, child_tags)

            # Reminders for this page, appended below the tree
            for i, (kind, data) in enumerate(page_items):
                tag = TAGS[i]
                if kind != "rem":
                    continue
                record_id, job_id = data
                r = rem_by_id.get(record_id)
                if not r:
                    continue
                log_msg(f"view bins {r = }")
                label = self._render_reminder_label(r)
                rows.append(
                    f"    [dim]{tag}[/dim] {label}"
                )  # 4-space indent to align with depth-1

            # Insert breadcrumb as FIRST row in the list (no page indicator here)
            rows.insert(0, crumb_txt)

            pages.append((rows, page_tag_map))

        # Title is just the crumb text; page indicator is added in _refresh_header
        return pages, crumb_txt

    def _render_tree_rows(
        self,
        flat_nodes: list[tuple[int, str, int]],
        child_tags: dict[int, str],
    ) -> list[str]:
        """
        Render the pre-ordered subtree as simple indented lines.

        • No box/branch glyphs.
        • Skip the root row (depth==0) so the current bin name is not repeated.
        • Insert inline tags for depth-1 nodes that are on the current page.
        """
        rows: list[str] = []
        for bid, name, depth in flat_nodes:
            if depth == 0:
                continue  # skip the current bin itself
            indent = "    " * depth
            tag_prefix = (
                f"[dim]{child_tags[bid]}[/dim] "
                if (depth == 1 and bid in child_tags)
                else ""
            )
            rows.append(
                f"{indent}{tag_prefix}[{TYPE_TO_COLOR['b']}]{name}[/ {TYPE_TO_COLOR['b']}]"
            )
        return rows

    def _render_tree_rows(
        self,
        flat_nodes: list[tuple[int, str, int]],
        child_tags: dict[int, str],
    ) -> list[str]:
        """
        Render the pre-ordered subtree as simple indented lines.

        • No box/branch glyphs.
        • Skip the root row (depth==0) so the current bin name is not repeated.
        • Insert inline tags for depth-1 nodes that are on the current page.
        • If a child's name looks like "PARENT:SUFFIX" where PARENT == parent's name,
          display only "SUFFIX".
        """
        rows: list[str] = []
        # Track last seen name at each depth to know the parent name
        last_name_at_depth: dict[int, str] = {}

        for bid, name, depth in flat_nodes:
            if depth == 0:
                # Root row: remember its name but don't render it here
                last_name_at_depth[0] = name
                continue

            # Remember this bin's name at its depth
            last_name_at_depth[depth] = name

            # Determine parent name (if any)
            parent_name = last_name_at_depth.get(depth - 1, "")

            # Default display name is the full name
            display_name = name

            # If "PARENT:rest" and PARENT matches parent_name, show only "rest"
            if parent_name and ":" in name:
                prefix, suffix = name.split(":", 1)
                if prefix == parent_name:
                    display_name = suffix

            indent = "    " * depth
            tag_prefix = (
                f"[dim]{child_tags[bid]}[/dim] "
                if (depth == 1 and bid in child_tags)
                else ""
            )
            rows.append(
                f"{indent}{tag_prefix}[{TYPE_TO_COLOR['b']}]{display_name}[/ {TYPE_TO_COLOR['b']}]"
            )

        return rows

    def _render_reminder_label(self, r: ReminderRow) -> str:
        # Example: "Fix itinerary  [dim]task[/dim]"
        log_msg(f"view bins {r = }")
        tclr = TYPE_TO_COLOR[r.itemtype]
        return f"[{tclr}]{r.itemtype} {r.subject}[/ {tclr}]"


###^^^ new for tagged bin screen


class DynamicViewApp(App):
    """A dynamic app that supports temporary and permanent view changes."""

    CSS_PATH = "view_textual.css"
    VIEW_REFRESHERS = {
        "weeks": "action_show_weeks",
        "agenda": "action_show_agenda",
        # ...
    }

    digit_buffer = reactive([])
    # afill = 1
    search_term = reactive("")

    BINDINGS = [
        # global
        # (".", "center_week", ""),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        ("ctrl+s", "take_screenshot", "Take Screenshot"),
        ("escape", "close_details", "Close details"),
        ("R", "show_alerts", "Show Alerts"),
        ("A", "show_agenda", "Show Agenda"),
        ("B", "show_bins", "Bins"),
        ("L", "show_last", "Show Last"),
        ("N", "show_next", "Show Next"),
        ("F", "show_find", "Find"),
        ("W", "show_weeks", "Weeks"),
        ("?", "show_help", "Help"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+n", "new_reminder", "Add new reminder"),
        ("ctrl+r", "detail_repetitions", "Show Repetitions"),
        ("/", "start_search", "Search"),
        (">", "next_match", "Next Match"),
        ("<", "previous_match", "Previous Match"),
        ("ctrl+z", "copy_search", "Copy Search"),
        ("ctrl-b", "show_bin", "Bin"),
    ]

    def __init__(self, controller) -> None:
        super().__init__()
        self.controller = controller
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self.title = ""
        self.view_mode = "list"
        self.view = "weeks"
        self.saved_lines = []
        self.afill = 1
        self.leader_mode = False
        self.details_drawer: DetailsDrawer | None = None
        self.run_daily_tasks()

    async def on_mount(self):
        self.styles.background = "#373737"
        try:
            screen = self.screen
            # screen.styles.background = "#2e2e2e"
            screen.styles.background = "#373737 100%"
            screen.styles.opacity = "100%"
            # optional: explicitly make some known child widgets transparent
            for sel in ("#list", "#main-list", "#details-list", "#table"):
                try:
                    w = screen.query_one(sel)
                    w.styles.background = "#373737 100%"
                    w.styles.opacity = "100%"
                except Exception:
                    pass
        except Exception:
            pass
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
        NOTE: uses week_tag_to_id for 'week' view, list_tag_to_id otherwise.
        """
        if self.view == "weeks":
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
            # from tklr.view import DetailsScreen

            self.push_screen(DetailsScreen([title] + lines))

    def make_detail_key_handler(self, *, view_name: str, week_provider=None):
        ctrl = self.controller
        app = self

        async def handler(key: str, meta: dict) -> None:  # chord-aware
            log_msg(f"in handler with {key = }, {meta = }")
            record_id = meta.get("record_id")
            job_id = meta.get("job_id")
            first = meta.get("first")
            second = meta.get("second")
            itemtype = meta.get("itemtype")
            subject = meta.get("subject")

            if not record_id:
                return

            # chord-based actions
            if key == "comma,f" and itemtype in "~^":
                log_msg(f"{record_id = }, {job_id = }, {first = }")
                job = f" {job_id}" if job_id else ""
                id = f"({record_id}{job})"
                due = (
                    f"\nDue: [{LIGHT_SKY_BLUE}]{fmt_user(first)}[/{LIGHT_SKY_BLUE}]"
                    if first
                    else ""
                )
                msg = f"Finished datetime\nFor: [{LIGHT_SKY_BLUE}]{subject} {id}[/{LIGHT_SKY_BLUE}]{due}"

                dt = await app.prompt_datetime(msg)
                if dt:
                    ctrl.finish_task(record_id, job_id=job_id, when=dt)

            # elif key == "comma,e":
            #     seed_text = ctrl.get_entry_from_record(record_id)
            #     log_msg(f"{seed_text = }")
            #     app.push_screen(EditorScreen(ctrl, record_id, seed_text=seed_text))

            elif key == "comma,e":
                # 1) Get editable text for this record
                seed_text = ctrl.get_entry_from_record(record_id)
                log_msg(f"{seed_text = }")

                # 2) Close/hide details before opening the editor to avoid stale view
                try:
                    scr = app.screen
                    if (
                        hasattr(scr, "list_with_details")
                        and scr.list_with_details.has_details_open()
                    ):
                        # adjust this to your actual API; many people have hide_details()
                        if hasattr(scr.list_with_details, "hide_details"):
                            scr.list_with_details.hide_details()
                except Exception as e:
                    log_msg(f"Error while hiding details before edit: {e}")

                # 3) Define callback to refresh after editor closes

                # 4) Push editor with callback
                app.push_screen(
                    EditorScreen(ctrl, record_id, seed_text=seed_text),
                    callback=self._after_edit,
                )

            elif key == "comma,c":
                row = ctrl.db_manager.get_record(record_id)
                seed_text = row[2] or ""
                app.push_screen(EditorScreen(ctrl, None, seed_text=seed_text))

            elif key == "comma,d":
                app.confirm(
                    f"Delete item {record_id}? This cannot be undone.",
                    lambda: ctrl.delete_item(record_id, job_id=job_id),
                )

            elif key == "comma,s":
                dt = await app.prompt_datetime("Schedule when?")
                if dt:
                    ctrl.schedule_new(record_id, when=dt)

            elif key == "comma,r":
                dt = await app.prompt_datetime("Reschedule to?")
                if dt:
                    yrwk = week_provider() if week_provider else None
                    ctrl.reschedule(record_id, when=dt, context=view_name, yrwk=yrwk)

            elif key == "comma,t":
                ctrl.touch_item(record_id)

            elif key == "comma,p" and itemtype == "~":
                ctrl.toggle_pinned(record_id)
                if hasattr(app, "_reopen_details"):
                    app._reopen_details(tag_meta=meta)

            # keep ctrl+r for repetitions
            elif key == "ctrl+r" and itemtype == "~":
                ctrl.show_repetitions(record_id)

        return handler

    def on_key(self, event: events.Key) -> None:
        """Handle global key events (tags, escape, etc.)."""
        log_msg(f"before: {event.key = }, {self.leader_mode = }")

        # --- View-specific setup ---
        log_msg(f"{self.view = }")
        # ------------------ improved left/right handling ------------------
        # if event.key == "ctrl+b":
        #     self.action_show_bins()

        if event.key in ("left", "right"):
            if self.view == "weeks":
                screen = getattr(self, "screen", None)
                # log_msg(
                #     f"[LEFT/RIGHT] screen={type(screen).__name__ if screen else None}"
                # )

                if not screen:
                    log_msg("[LEFT/RIGHT] no screen -> fallback week nav")
                    if event.key == "left":
                        self.action_previous_week()
                    else:
                        self.action_next_week()
                    return

                # check both "has method" and the result of calling it (if callable)
                has_prev_method = getattr(screen, "has_prev_page", None)
                has_next_method = getattr(screen, "has_next_page", None)
                do_prev = callable(getattr(screen, "previous_page", None))
                do_next = callable(getattr(screen, "next_page", None))

                has_prev_callable = callable(has_prev_method)
                has_next_callable = callable(has_next_method)

                # call them (safely) to get boolean availability
                try:
                    has_prev_available = (
                        has_prev_method() if has_prev_callable else False
                    )
                except Exception as e:
                    log_msg(f"[LEFT/RIGHT] has_prev_page() raised: {e}")
                    has_prev_available = False

                try:
                    has_next_available = (
                        has_next_method() if has_next_callable else False
                    )
                except Exception as e:
                    log_msg(f"[LEFT/RIGHT] has_next_page() raised: {e}")
                    has_next_available = False

                # Prefer page navigation when page available; otherwise fallback to week nav.
                if event.key == "left":
                    if has_prev_available and do_prev:
                        log_msg("[LEFT/RIGHT] -> screen.previous_page()")
                        screen.previous_page()
                    else:
                        log_msg("[LEFT/RIGHT] -> no prev page -> previous week")
                        self.action_previous_week()
                    return

                else:  # right
                    if has_next_available and do_next:
                        log_msg("[LEFT/RIGHT] -> screen.next_page()")
                        screen.next_page()
                    else:
                        log_msg("[LEFT/RIGHT] -> no next page -> next week")
                        self.action_next_week()
                    return
            # else: not week view -> let other code handle left/right
        if event.key == "full_stop" and self.view == "weeks":
            # call the existing "center_week" or "go to today" action
            try:
                self.action_center_week()  # adjust name if different
            except Exception:
                pass
            # reset pages if screen supports it
            if hasattr(self.screen, "reset_to_first_page"):
                self.screen.reset_to_first_page()
            return

        if event.key == "escape":
            if self.leader_mode:
                self.leader_mode = False
                return
            if self.view == "bin":
                self.pop_screen()
                self.view = "bintree"
                return

        # --- Leader (comma) mode ---
        if event.key == "comma":
            self.leader_mode = True
            log_msg(f"set {self.leader_mode = }")
            return

        if self.leader_mode:
            self.leader_mode = False
            meta = self.controller.get_last_details_meta() or {}
            handler = getattr(self, "detail_handler", None)
            log_msg(f"got {event.key = }, {handler = }")
            if handler:
                log_msg(f"creating task for {event.key = }, {meta = }")
                create_task(handler(f"comma,{event.key}", meta))
            return

        # inside DynamicViewApp.on_key, after handling leader/escape etc.
        screen = self.screen  # current active Screen (FullScreenList, WeeksScreen, ...)
        key = event.key

        # --- Page navigation (left / right) for any view that provides it ----------
        if key in ("right",):  # pick whichever keys you bind for next page
            if hasattr(screen, "next_page"):
                try:
                    screen.next_page()
                    return
                except Exception as e:
                    log_msg(f"next_page error: {e}")
        # previous page
        if key in ("left",):  # your left binding(s)
            if hasattr(screen, "previous_page"):
                try:
                    screen.previous_page()
                    return
                except Exception as e:
                    log_msg(f"previous_page error: {e}")

        # --- Single-letter tag press handling for paged views ----------------------
        # (Note: we assume tags are exactly one lower-case ASCII letter 'a'..'z')
        if key in "abcdefghijklmnopqrstuvwxyz":
            # If the view supplies a show_details_for_tag method, use it
            if hasattr(screen, "show_details_for_tag"):
                screen.show_details_for_tag(key)
        return

    def action_take_screenshot(self):
        path = timestamped_screenshot_path(self.view)
        self.save_screenshot(str(path))
        log_msg(f"Screenshot saved to: {path}")

    def run_daily_tasks(self):
        created, kept, removed = self.controller.rotate_daily_backups()
        if created:
            log_msg(f"✅ Backup created: {created}")
        else:
            log_msg("ℹ️ No backup created (DB unchanged since last snapshot).")
        if removed:
            log_msg("🧹 Pruned: " + ", ".join(p.name for p in removed))

        self.controller.populate_alerts()
        self.controller.populate_notice()

    def play_bells(self) -> None:
        """An action to ring the bell."""
        delay = [0.6, 0.4, 0.2]
        for d in delay:
            time.sleep(d)  # ~400 ms gap helps trigger distinct alerts
            self.app.bell()

    async def check_alerts(self):
        # called every 6 seconds
        now = datetime.now()
        if now.hour == 0 and now.minute == 0 and 0 <= now.second < 6:
            self.run_daily_tasks()
        if now.minute % 10 == 0 and now.second == 0:
            # check alerts every 10 minutes
            self.notify(
                "Checking for scheduled alerts...", severity="info", timeout=1.2
            )
        # execute due alerts
        due = self.controller.get_due_alerts(now)  # list of [alert_id, alert_commands]
        if not due:
            return
        for alert_id, alert_name, alert_command in due:
            if alert_name == "n":
                self.notify(f"{alert_command}", timeout=60)
                play_alert_sound("alert.mp3")
            else:
                os.system(alert_command)
            self.controller.db_manager.mark_alert_executed(alert_id)

    # def action_new_reminder(self):
    #     self.push_screen(EditorScreen(self.controller, None, seed_text=""))

    def action_new_reminder(self) -> None:
        # Use whatever seed you like (empty, template, clipboard, etc.)
        self.open_editor_for(seed_text="")

    def show_screen(self, screen: Screen) -> None:
        """Use switch_screen when possible; fall back to push_screen initially."""
        try:
            self.switch_screen(screen)
        except IndexError:
            # No screen to switch from yet; first main screen
            self.push_screen(screen)

    def refresh_view(self) -> None:
        view_name = getattr(self, "view", None)
        if not view_name:
            return

        method_name = self.VIEW_REFRESHERS.get(view_name)
        log_msg(f"{view_name = }, {method_name = }")
        if not method_name:
            return

        method = getattr(self, method_name, None)
        if callable(method):
            method()

    def action_show_weeks(self):
        self.view = "weeks"
        title, table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        # self.set_afill("weeks")

        screen = WeeksScreen(title, table, details, footer)
        self.show_screen(screen)

    def action_show_agenda(self):
        self.view = "agenda"
        details, title = self.controller.get_agenda()
        # footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

        return

    def action_show_bin(self, bin_id: Optional[int] = None):
        self.view = "bin"
        if bin_id is None:
            bin_id = self.controller.root_id
        self.show_screen(BinView(controller=self.controller, bin_id=bin_id))

    def action_show_last(self):
        self.view = "last"
        details, title = self.controller.get_last()
        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

    def action_show_next(self):
        self.view = "next"
        details, title = self.controller.get_next()
        log_msg(f"{details = }, {title = }")

        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

    def action_show_find(self):
        self.view = "find"
        search_input = Input(placeholder="Enter search term...", id="find_input")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_show_alerts(self):
        self.view = "alerts"
        pages, header = self.controller.get_active_alerts()
        log_msg(f"{pages = }, {header = }")

        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"

        self.push_screen(
            FullScreenList(pages, "Active Alerts for Today", header, footer)
        )

    def _close_details_if_open(self) -> None:
        # If your details is a modal screen, pop it; if it's a panel, hide it.
        try:
            scr = self.screen
            if (
                hasattr(scr, "list_with_details")
                and scr.list_with_details.has_details_open()
            ):
                scr.list_with_details.hide_details()  # or details.visible = False / self.app.pop_screen()
        except Exception:
            pass

    # def _after_edit(self, result: dict | None) -> None:
    #     if not result:
    #         return
    #     if result.get("changed"):
    #         rid = result.get("record_id")
    #         self.refresh_view()
    #         # Optionally re-open/show details for the updated/created record:
    #         if rid is not None and hasattr(self, "open_details"):
    #             self.open_details(rid)

    def _after_edit(self, result: dict | None) -> None:
        if not result or not result.get("changed"):
            return
        rid = result.get("record_id")

        self.refresh_view()

        if rid is not None and hasattr(self, "open_details"):
            self.open_details(rid)

    def open_editor_for(
        self, *, record_id: int | None = None, seed_text: str = ""
    ) -> None:
        self._close_details_if_open()
        self.app.push_screen(
            EditorScreen(self.controller, record_id=record_id, seed_text=seed_text),
            callback=self._after_edit,
        )

    def on_input_submitted(self, event: Input.Submitted):
        search_term = event.value
        event.input.remove()

        if event.input.id == "find_input":
            self.view = "find"
            results, title = self.controller.find_records(search_term)
            footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
            self.show_screen(FullScreenList(results, title, "", footer))

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
            log_msg("[App] Current screen does not support search.")

    def action_copy_search(self) -> None:
        screen = getattr(self, "screen", None)
        term = ""
        if screen is not None and hasattr(screen, "get_search_term"):
            try:
                term = screen.get_search_term() or ""
            except Exception:
                term = ""
        else:
            term = getattr(self, "search_term", "") or ""

        if not term:
            self.notify("Nothing to copy", severity="info", timeout=1.2)
            return

        try:
            copy_to_clipboard(term)
            self.notify("Copied search to clipboard ✓", severity="info", timeout=1.2)
        except ClipboardUnavailable as e:
            self.notify(f"{str(e)}", severity="error", timeout=1.2)

    def update_table_and_list(self):
        screen = self.screen
        if isinstance(screen, WeeksScreen):
            screen.update_table_and_list()

    def action_current_period(self):
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_next_period(self):
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_previous_period(self):
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_next_week(self):
        self.selected_week = get_next_yrwk(*self.selected_week)
        if self.selected_week > tuple(
            (self.current_start_date + timedelta(weeks=4) - ONEDAY).isocalendar()[:2]
        ):
            self.current_start_date += timedelta(weeks=1)
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_previous_week(self):
        self.selected_week = get_previous_yrwk(*self.selected_week)
        if self.selected_week < tuple((self.current_start_date).isocalendar()[:2]):
            self.current_start_date -= timedelta(weeks=1)
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_center_week(self):
        self.current_start_date = datetime.strptime(
            f"{self.selected_week[0]} {self.selected_week[1]} 1", "%G %V %u"
        ) - timedelta(weeks=1)
        self.update_table_and_list()

    def action_quit(self):
        self.exit()

    # def action_show_help(self):
    #     self.push_screen(HelpScreen(HelpText))

    def action_show_help(self):
        scr = self.screen
        log_msg(
            f"{scr = }, {self.controller.get_last_details_meta() = }, {hasattr(scr, 'list_with_details') = }"
        )
        if (
            hasattr(scr, "list_with_details")
            and scr.list_with_details.has_details_open()
        ):
            meta = self.controller.get_last_details_meta() or {}
            lines = build_details_help(meta)
            self.push_screen(HelpScreen(lines))
        else:
            self.push_screen(HelpScreen(HelpText))

    def action_detail_edit(self):
        self._dispatch_detail_key("/e")

    def action_detail_copy(self):
        self._dispatch_detail_key("/c")

    def action_detail_delete(self):
        self._dispatch_detail_key("/d")

    def action_detail_finish(self):
        self._dispatch_detail_key("/f")

    def action_detail_pin(self):
        self._dispatch_detail_key("/p")

    def action_detail_schedule(self):
        self._dispatch_detail_key("/s")

    def action_detail_reschedule(self):
        self._dispatch_detail_key("/r")

    def action_detail_touch(self):
        self._dispatch_detail_key("/t")

    def action_detail_repetitions(self):
        self._dispatch_detail_key("ctrl+r")

    def _dispatch_detail_key(self, key: str) -> None:
        # Look at the current screen and meta
        scr = self.screen
        if (
            hasattr(scr, "list_with_details")
            and scr.list_with_details.has_details_open()
        ):
            meta = self.controller.get_last_details_meta() or {}
            handler = self.make_detail_key_handler(view_name=self.view)
            handler(key, meta)

    async def prompt_datetime(
        self, message: str, default: datetime | None = None
    ) -> datetime | None:
        """Show DatetimePrompt and return parsed datetime or None."""
        return await self.push_screen_wait(DatetimePrompt(message, default))

    def action_show_bins(self, start_bin_id: int | None = None):
        root_id = start_bin_id or self.controller.get_root_bin_id()
        self.push_screen(TaggedHierarchyScreen(self.controller, root_id))


if __name__ == "__main__":
    pass
