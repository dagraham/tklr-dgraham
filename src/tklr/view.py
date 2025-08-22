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
from textual.containers import Vertical
from textual.geometry import Size
from textual.reactive import reactive
from textual.screen import ModalScreen
from textual.screen import Screen
from textual.scroll_view import ScrollView
from textual.strip import Strip
from textual.widget import Widget
from textual.widgets import Input
from textual.widgets import Label
from textual.widgets import Markdown, Static, Footer, Header
from textual.widgets import Placeholder
import string
import shutil
import asyncio
from tklr.common import get_version

from rich.panel import Panel
from textual.containers import Container
from textual.containers import Horizontal

from typing import List, Optional, Any, Iterable
from textual.widgets import Button


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

    def _finish_task(self) -> None:
        if not self.is_task or self.record_id is None:
            return

        try:
            res = self.app.controller.finish_current_instance(self.record_id)
            # Nice little confirmation
            title = self._base_title()
            self.app.notify(f"Finished: {title}", timeout=1.5)

            # If it's now fully finished, update the title glyph too
            # (optional; your finish may flip to itemtype 'x')
            self._apply_pin_glyph()

            # ★ Refresh any open screen that knows how to reload itself (Agenda, etc.)

            for scr in list(getattr(self.app, "screen_stack", [])):
                if scr.__class__.__name__ == "AgendaScreen" and getattr(
                    scr, "refresh_data", None
                ):
                    scr.refresh_data()
                    break

            # Optionally auto-close the details modal
            self.app.pop_screen()

        except Exception as e:
            self.app.notify(f"Finish failed: {e}", severity="error", timeout=3)

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
        self.lines = [Text.from_markup(line) for line in new_lines]
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


class WeeksScreen(SearchableScreen):  # instead of Screen
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

    async def on_mount(self) -> None:
        self.update_table_and_list()

    def compose(self) -> ComposeResult:
        yield Static(
            self.table_title or "Untitled", id="table_title", classes="title-class"
        )
        yield Static(self.table or "[i]No data[/i]", id="table", classes="weeks-table")
        yield Static(self.list_title, id="list_title", classes="title-class")
        yield ScrollableList(self.details, id="list")
        # yield Static(self.footer_content, id="details_footer")
        yield Static(self.footer_content)

    def update_table_and_list(self):
        title, table, details = self.app.controller.get_table_and_list(
            self.app.current_start_date, self.app.selected_week
        )
        self.query_one("#table_title", expect_type=Static).update(title)
        self.query_one("#table", expect_type=Static).update(table)
        self.query_one("#list_title", expect_type=Static).update(details[0])
        self.query_one("#list", expect_type=ScrollableList).update_list(details[1:])


class AgendaScreen(SearchableScreen):  # ← inherit your base
    BINDINGS = [
        ("tab", "toggle_pane", "Switch Pane"),
        ("r", "refresh", "Refresh"),
        ("A", "refresh", "Agenda"),
        # Do NOT bind "/" here if your App already handles it globally.
        # Same for n/N/Esc if the App routes those to the current screen.
    ]

    def __init__(self, controller, footer: str = ""):
        super().__init__()
        self.controller = controller
        self.footer_text = f"[{FOOTER}]?[/{FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search  [bold {FOOTER}]tab[/bold {FOOTER}] Switch panes"
        self.active_pane = "tasks"
        self.events_list: ScrollableList | None = None
        self.tasks_list: ScrollableList | None = None
        self.events = {}
        self.tasks = []

    def on_screen_resume(self) -> None:
        if self.app.controller.consume_agenda_dirty():
            log_msg("refreshing")
            self.refresh_data()

    # ← This is the only thing SearchableScreen needs to work with panes
    def get_search_target(self) -> ScrollableList:
        return self.tasks_list if self.active_pane == "tasks" else self.events_list

    def compose(self) -> ComposeResult:
        self.events_list = ScrollableList([], id="events")
        self.tasks_list = ScrollableList([], id="tasks")
        yield Vertical(
            Container(
                Static("Events", id="events_title"), self.events_list, id="events-pane"
            ),
            Container(
                Static("Tasks", id="tasks_title"), self.tasks_list, id="tasks-pane"
            ),
            Static(self.footer_text),
            # Footer(),
            id="agenda-layout",
        )

    def on_mount(self):
        self.refresh_data()
        self._activate_pane("tasks")

    def _activate_pane(self, which: str):
        self.active_pane = which
        self.set_focus(self.get_search_target())
        self.app.view = which  # if you use this for tag→id routing
        ev = self.query_one("#events_title", Static)
        tk = self.query_one("#tasks_title", Static)
        if which == "events":
            tk.add_class("inactive")
            ev.remove_class("inactive")
        else:
            ev.add_class("inactive")
            tk.remove_class("inactive")

    def action_toggle_pane(self):
        # self._activate_pane("tasks" if self.active_pane == "events" else "events")
        self._activate_pane("events" if self.active_pane == "tasks" else "tasks")

    def action_refresh(self):
        self.refresh_data()

    def refresh_data(self):
        try:
            self.events = self.controller.get_agenda_events(datetime.now())
        except TypeError:
            self.events = self.controller.get_agenda_events()
        self.tasks = self.controller.get_agenda_tasks()
        log_msg(f"{self.tasks = }")
        self.update_display()

    def update_display(self):
        event_lines = []
        for d, entries in self.events.items():
            event_lines.append(f"[bold]{d.strftime('%a %b %-d')}[/bold]")
            for tag, label, subject in entries:
                entry = f"{label} {subject}" if label and label.strip() else subject
                event_lines.append(f"{tag} {entry}".rstrip())

        task_lines = []
        for urgency, color, tag, subject in self.tasks:
            # if urgency == 1.0:
            #     urgency_str = "📌"
            # else:
            #     urgency_str = f"[{color}]{str(round(urgency * 100)):>2}[/{color}]"
            task_lines.append(f"{tag} {urgency} {subject}")

        self.events_list.update_list(event_lines)
        self.tasks_list.update_list(task_lines)


class FullScreenList(SearchableScreen):
    """Reusable full-screen list for Last, Next, and Find views."""

    def __init__(
        self,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        if details:
            self.title = details[0]  # First line is the title
            self.header = details[1]  # First line is also the header
            self.lines = details[2:]  # Remaining lines are scrollable content
        else:
            self.title = "Untitled"
            self.lines = []
        # self.footer_content = footer_content
        self.footer_content = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        log_msg(f"FullScreenList: {details[:3] = }")

    def compose(self) -> ComposeResult:
        """Compose the layout."""

        yield Static(self.title, id="scroll_title", expand=True, classes="title-class")
        yield Static(
            self.header, id="scroll_header", expand=True, classes="header-class"
        )
        yield ScrollableList(self.lines, id="list")  # Using "list" as the ID
        yield Static(self.footer_content, id="custom_footer")


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
        self.action_show_weeks()

        now = datetime.now()
        seconds_to_next = (6 - (now.second % 6)) % 6
        await asyncio.sleep(seconds_to_next)
        self.set_interval(6, self.check_alerts)

    def on_key(self, event):
        """Handle key events."""
        log_msg(f"{self.afill = }")

        if event.key in "abcdefghijklmnopqrstuvwxyz":
            # Handle lowercase letters
            self.digit_buffer.append(event.key)
            if len(self.digit_buffer) == self.afill:
                base26_tag = "".join(self.digit_buffer)
                self.digit_buffer.clear()
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
            # populate alerts hourly
            self.controller.populate_alerts()
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
        self.set_afill(details, "action_show_alerts")

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
        log_msg(f"{self.view = }, {self.selected_week = }, {tag = }")
        self.fill = self.controller.afill_by_week[self.selected_week]
        details = self.controller.process_tag(tag, self.view, self.selected_week)
        self.push_screen(DetailsScreen(details))


if __name__ == "__main__":
    pass
