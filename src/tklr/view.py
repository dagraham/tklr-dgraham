from __future__ import annotations

# import tklr
import os
import time
import urllib.request
import ssl
import certifi

import asyncio
from pathlib import Path

from .shared import (
    log_msg,
    bug_msg,
    parse,
    TYPE_TO_COLOR,
    fmt_user,
    get_previous_yrwk,
    get_next_yrwk,
    calculate_4_week_start,
)
from datetime import datetime, timedelta, date

# from logging import log
from packaging.version import parse as parse_version

# from rich import box
from rich.console import Console
from rich.segment import Segment
from rich.table import Table
from rich.text import Text
from rich.rule import Rule
from rich.style import Style
from textual.app import App, ComposeResult, ScreenStackError
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
from textual.widgets import OptionList
from textual import on
import shutil
import asyncio
from typing import Dict, Tuple
import pyperclip
from .item import Item
from .use_system import open_with_default, play_alert_sound
from .mask import reveal_mask_tokens

import re

from rich.panel import Panel
from textual.containers import Container

from typing import List, Callable, Optional, Any, Iterable, Tuple, Sequence, Union

# details_drawer.py
from textual import events

from textual.events import Key
from .versioning import get_version
from pathlib import Path

from dataclasses import dataclass
import json

from .query import QueryMatch, QueryError
from tklr.tklr_env import collapse_home


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

# SCREENSHOT_BINDING = "ctrl+shift+s"
SCREENSHOT_BINDING = "ctrl+r"
SAVE_BINDING = "ctrl+s"
SAVE_LABEL = "^s"
CANCEL_BINDING = "ctrl+escape"
CANCEL_LABEL = "^esc"
NOTE_COLOR = DARK_SALMON
NOTICE_COLOR = GOLD

# Styles that differ by theme (mutated at runtime)
FOOTER_DARK = "#FF8C00"
FOOTER_LIGHT = "#1660a0"
FOOTER = FOOTER_DARK
DIM_STYLE_DARK = "dim"
DIM_STYLE_LIGHT = "#4a4a4a"
DIM_STYLE = DIM_STYLE_DARK
UPDATE_CHECK_PACKAGE = "tklr-dgraham"
UPDATE_CHECK_TIMEOUT = 2.0
_TLS_CONTEXT = ssl.create_default_context(cafile=certifi.where())


def check_update_available(
    current_version,
    package: str = UPDATE_CHECK_PACKAGE,
    timeout: float = UPDATE_CHECK_TIMEOUT,
) -> bool:
    """
    Query PyPI for the latest published version and return True when a newer
    release is available. Failures are silent so the UI never blocks startup.
    """
    bug_msg(f"[update-check] Current version: {current_version}")
    log_msg(f"[update-check] Current version: {current_version}")
    if os.environ.get("TKLR_SKIP_UPDATE_CHECK"):
        return False

    url = f"https://pypi.org/pypi/{package}/json"
    try:
        with urllib.request.urlopen(
            url, timeout=timeout, context=_TLS_CONTEXT
        ) as response:
            payload = json.load(response)
    except Exception as exc:  # pragma: no cover - network best effort
        log_msg(f"[update-check] Unable to reach PyPI: {exc}")
        return False

    latest_str = (payload.get("info") or {}).get("version")
    # bug_msg(f"[update-check] Latest version string from PyPI: {latest_str}")
    if not latest_str:
        return False

    try:
        latest_version = parse_version(latest_str)
        # bug_msg(f"[update-check] Latest version on PyPI: {latest_version = }")
    except Exception as exc:
        log_msg(f"[update-check] Invalid PyPI version '{latest_str}': {exc}")
        return False

    try:
        return latest_version > current_version
    except Exception:
        return False


# This one appears to be a Rich/Textual style string
SELECTED_COLOR = "bold yellow"

ONEDAY = timedelta(days=1)
ONEWK = 7 * ONEDAY


# TYPE_TO_COLOR - moved to shared.py


def build_details_help(meta: dict) -> list[str]:
    subject = meta.get("subject")

    lines = [
        f"[bold {TITLE_COLOR}]{subject or '- Details -'}[/bold {TITLE_COLOR}]",
        "",
        "[bold]Enter[/bold] Open reminder menu",
        "[bold]Esc[/bold] Close details view",
    ]
    return lines


def meta_times(meta: dict) -> dict:
    return {x: meta.get(x, "") for x in ["subject", "first", "second", "instance_ts"]}
    # return "\n".join(
    #     [
    #         f"{x}: {meta.get(x, '')}"
    #         for x in ["subject", "first", "second", "instance_ts"]
    #     ]
    # )


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


def build_help_text(home: str | None = None) -> list[str]:
    home_suffix = f" — {home}" if home else ""
    text = f"""\
[bold][{TITLE_COLOR}]tklr {VERSION}{home_suffix}[/{TITLE_COLOR}][/bold]
The current version of tklr is given above. When
a newer version is available, a "𝕦" will appear
in the footer area of the main views. You can also
check for updates manually by pressing [bold]^u[/bold], i.e.,
pressing [bold]control[/bold] and [bold]u[/bold] simultaneously.
[bold][{HEADER_COLOR}]Key Bindings[/{HEADER_COLOR}][/bold]
[bold]^q[/bold]    Quit               [bold]^r[/bold]    Record Screenshot
[bold] +[/bold]    New Reminder       [bold] Y[/bold]    Yearly Calendar
[bold][{HEADER_COLOR}]Views[/{HEADER_COLOR}][/bold]
 [bold]A[/bold]    Agenda              [bold]M[/bold]    Modified
 [bold]B[/bold]    Bins                [bold]N[/bold]    Next
 [bold]C[/bold]    Completions         [bold]Q[/bold]    Query
 [bold]F[/bold]    Find                [bold]R[/bold]    Remaining Alerts
 [bold]G[/bold]    Goals               [bold]T[/bold]    Tags
 [bold]L[/bold]    Last                [bold]W[/bold]    Weeks
[bold][{HEADER_COLOR}]Weeks View Navigation[/{HEADER_COLOR}][/bold]
 Left/Right cursor keys move by one week.
   Add Shift to jump by 4 weeks.
 Press "J" to jump to a specific date
   or "space" to jump to the current date.
[bold][{HEADER_COLOR}]Tags and Reminder Details[/{HEADER_COLOR}][/bold]
 Each of the views listed above displays a list
 of items. In these listings, each item begins
 with a tag sequentially generated from 'a', 'b',
 ..., 'z'. When more than 26 tags are required,
 additional pages are appended with left and right
 cursor keys used to move between pages and up and
 down keys to scroll in the list.  Press the
 key of the tag on your keyboard to see the
 details of the item and access related commands
 to edit, reschedule, finish and so forth. To see
 the complete list of available commands press ?
 when the details pane is open.
[bold][{HEADER_COLOR}]Search[/{HEADER_COLOR}][/bold]
 Press "/" and enter expression to search
   or enter nothing to clear search highlighting.
 While search is active, press "[bold]<[/bold]" and "[bold]>[/bold]"
   to step through matches.
"""
    return text.splitlines()


QueryHelpText = f"""\
[bold][{TITLE_COLOR}]Query Builder[{TITLE_COLOR}][/bold]
[bold][{HEADER_COLOR}]Syntax[/{HEADER_COLOR}][/bold]
 command field [args]
 Fields → itemtype, subject or any @-key (b, d, s, ...)
 Commands:
   begins field RGX      · value begins with RGX
   in(cludes) fields RGX · any listed field matches RGX
   equals field VALUE    · exact match
   more/less field VALUE · numeric/string comparisons
   exists field          · field present
   any/all/one field LST · list membership tests
   info ID               · open record by id
   dt field EXP          · date/time queries
 Prefix a command with '~' to negate it.
 Combine clauses with 'and' / 'or'.

[bold][{HEADER_COLOR}]Examples[/{HEADER_COLOR}][/bold]
 begins subject waldo
 ~includes subject waldo
 includes subject d projectX
 dt s < 2024-07-01 and equals itemtype *
""".splitlines()


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

    def __init__(self, segments: list[int], *, label_style: str | None = None):
        assert len(segments) == 35, "Expected 35 slots (7×5)"
        super().__init__()
        self.segments = segments
        self.label_style = label_style or "bold cyan"

    def render(self) -> Text:
        # Row 1: labels
        text = Text()
        for d, lbl in enumerate(self.day_labels):
            text.append(f"| {lbl} |", style=self.label_style)
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


class FooterDisplay(Static):
    """Primary footer text block used in dialogs/modals."""

    def __init__(self, text: str, **kwargs):
        self._base_text = text
        kwargs.setdefault("id", "custom_footer")
        super().__init__(text, **kwargs)

    def update(self, renderable):
        if isinstance(renderable, str):
            self._base_text = renderable
        return super().update(renderable)


class FooterNoticeBar(Static):
    """Footer with main text on the left and an indicator on the right."""

    def __init__(self, text: str, **kwargs):
        self._text = text
        kwargs.setdefault("id", "custom_footer")
        super().__init__("", **kwargs)
        self.can_focus = False

    def _build_renderable(self) -> Table:
        indicator = ""
        app = getattr(self, "app", None)
        if app:
            indicator = getattr(app, "update_indicator_text", "") or ""
        table = Table.grid(padding=(0, 0), expand=True)
        table.add_column(ratio=1)
        table.add_column(no_wrap=True, justify="right")
        table.add_row(
            Text.from_markup(self._text),
            Text.from_markup(indicator) if indicator else Text(""),
        )
        return table

    def update(self, renderable):
        if isinstance(renderable, str):
            self._text = renderable
            renderable = self._build_renderable()
        return super().update(renderable)

    def on_mount(self) -> None:
        self.update(self._build_renderable())

    def refresh_indicator(self) -> None:
        self.update(self._build_renderable())


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
        self._details_history: list[tuple[str, list[str], dict | None]] = []
        self._current_details: tuple[str, list[str], dict | None] | None = None
        self._details_visibility_callback: Callable[[bool], None] | None = None
        self._footer_hint_active = False
        self._footer_saved_text: str | None = None

    def on_mount(self):
        bg_color = getattr(self.app, "list_bg_color", "#373737")
        # 1) Set the widget backgrounds (outer)
        for w in (self._main, self._details):
            if not w:
                continue
            if hasattr(w, "set_background_color"):
                w.set_background_color(bg_color)
            elif hasattr(w, "styles"):
                w.styles.background = bg_color

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

        force_scroller_bg(self._main, bg_color)
        force_scroller_bg(self._details, bg_color)

        # 3) (Optional) make the container itself non-transparent
        if hasattr(self, "styles"):
            self.styles.background = bg_color

        def _dump_chain(widget):
            w = widget
            depth = 0
            while w is not None:
                try:
                    bg = w.styles.background
                except Exception:
                    bg = "<no styles.background>"
                w = getattr(w, "parent", None)
                depth += 1

        try:
            m = self.query_one("#main-list")
            _dump_chain(m)
        except Exception as e:
            log_msg(f"debug: couldn't find #main-list: {e}")

    def compose(self):
        # Background filler behind the lists
        # yield Static("", id="list-bg")
        bg_color = getattr(self.app, "list_bg_color", "#373737")
        text_color = getattr(self.app, "list_text_color", None)
        self._main = ScrollableList(
            [], id="main-list", bg_color=bg_color, text_color=text_color
        )
        self._details = ScrollableList(
            [], id="details-list", bg_color=bg_color, text_color=text_color
        )
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
        self,
        title: str,
        lines: list[str],
        meta: dict | None = None,
        *,
        push_history: bool = False,
    ) -> None:
        if (
            push_history
            and self.has_details_open()
            and self._current_details is not None
        ):
            self._details_history.append(self._current_details)
        self.details_meta = meta or {}  # <- keep meta for key actions
        body = _make_rows(lines)
        self._details.update_list(body)
        self._details.remove_class("hidden")
        self._details_active = True
        self._details.focus()
        self._current_details = (title, lines, meta)
        if self._details_visibility_callback:
            self._details_visibility_callback(True)
        self._set_footer_hint(True)

    def hide_details(self) -> None:
        self.details_meta = {}  # clear meta on close
        if not self._details.has_class("hidden"):
            self._details_active = False
            self._details.add_class("hidden")
            self._main.focus()
        self._details_history.clear()
        self._current_details = None
        if self._details_visibility_callback:
            self._details_visibility_callback(False)
        self._set_footer_hint(False)

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

    def set_details_visibility_callback(self, callback: Callable[[bool], None]) -> None:
        self._details_visibility_callback = callback

    def on_key(self, event) -> None:
        """Only handle detail commands; let lowercase tag keys bubble up."""
        if not self.has_details_open():
            return

        k = event.key or ""
        lower_k = k.lower()

        if k == "enter":
            if self._detail_key_handler:
                self._detail_key_handler("ENTER", self.details_meta or {})
                event.stop()
            return

        # 1) Let lowercase a–z pass through (tag selection)
        if len(k) == 1 and "a" <= k <= "z":
            # do NOT stop the event; DynamicViewApp will collect the tag chars
            return

        # 2) Close details with Escape (but not 'q')
        if k == "escape":
            if self._details_history:
                prev_title, prev_lines, prev_meta = self._details_history.pop()
                self.show_details(prev_title, prev_lines, prev_meta, push_history=False)
            elif self.has_details_open():
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

    def _set_footer_hint(self, active: bool) -> None:
        app = getattr(self, "app", None)
        screen = getattr(app, "screen", None) if app else None
        if not screen:
            return
        try:
            footer = screen.query_one("#custom_footer", Static)
        except Exception:
            return

        hint = f"  [bold {FOOTER}]Enter[/bold {FOOTER}] Reminder menu"

        if active:
            if self._footer_hint_active:
                return
            base_text = getattr(screen, "footer_content", None)
            if not base_text:
                renderable = getattr(footer, "renderable", "")
                base_text = (
                    renderable if isinstance(renderable, str) else str(renderable)
                )
            self._footer_saved_text = (
                base_text if isinstance(base_text, str) else str(base_text)
            )
            footer.update(f"{self._footer_saved_text}{hint}")
            self._footer_hint_active = True
        else:
            if not self._footer_hint_active:
                return
            base_text = getattr(screen, "footer_content", "")
            if not base_text:
                base_text = self._footer_saved_text or ""
            footer.update(base_text)
            self._footer_hint_active = False
            self._footer_saved_text = None

    def _copy_details_to_clipboard(
        self, title: str, lines: list[str], meta: dict | None
    ) -> tuple[bool, str | None]:
        """Copy the entry string derived from tokens to the system clipboard."""
        entry_text = (meta or {}).get("entry_text", "")
        payload = entry_text.strip() if isinstance(entry_text, str) else ""
        if not payload:
            chunks: list[str] = []
            if title:
                chunks.append(title.strip())
            if lines:
                chunks.append(
                    "\n".join(line.rstrip() for line in lines if line is not None)
                )
            payload = "\n\n".join(chunk for chunk in chunks if chunk).strip()
        if not payload:
            return False, "Nothing to copy"
        try:
            copy_to_clipboard(payload)
        except ClipboardUnavailable as exc:
            log_msg(f"[Clipboard] Unable to copy details: {exc}")
            return False, str(exc)
        except Exception as exc:
            log_msg(f"[Clipboard] Unexpected error: {exc}")
            return False, "Unable to copy details"
        return True, None


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


class OptionPrompt(ModalScreen[Optional[str]]):
    """
    Modal screen offering a message + choice list using OptionList.

    Returns the chosen option label (string) or None on cancel (ESC).
    """

    BINDINGS = [
        (SCREENSHOT_BINDING, "take_screenshot", "Take Screenshot"),
    ]

    def __init__(self, message: str, options: Sequence[Union[str, tuple[str, str]]]):
        super().__init__()
        self.message = message.strip()
        processed: list[str] = []
        self._raw_options: list[str] = []
        self._explicit_hotkeys: list[tuple[str, str]] = []
        for opt in options:
            if isinstance(opt, tuple):
                label, hotkey = opt
                processed.append(label)
                self._raw_options.append(label)
                key = (hotkey or "").strip().lower()[:1]
                if key:
                    self._explicit_hotkeys.append((key, label))
            else:
                processed.append(opt)
                self._raw_options.append(opt)

        self.options = processed
        self._olist: OptionList | None = None
        self._hotkey_map: dict[str, str] = {}
        self._build_hotkey_map()

    def compose(self):
        with Vertical(id="option_prompt"):
            yield Static(" Select an option ", classes="title-class", id="option_title")

            if self.message:
                yield Static(self.message, id="option_message")

            if self._hotkey_map:
                instructions = (
                    "Either press an option's first letter to choose it "
                    "or use ↑/↓ to select and then [bold yellow]Enter[/bold yellow] "
                    "to choose or [bold yellow]ESC[/bold yellow] to cancel."
                )
            else:
                instructions = (
                    "Use ↑/↓ to move, [bold yellow]Enter[/bold yellow] to select, "
                    "[bold yellow]ESC[/bold yellow] to cancel."
                )

            yield Static(instructions, id="option_instructions")

            self._olist = OptionList(*self.options, id="option_list")
            yield self._olist

    def on_mount(self) -> None:
        # Make sure the list actually has focus
        self._olist = self.query_one("#option_list", OptionList)
        self._olist.focus()

    @on(OptionList.OptionSelected)
    def _on_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Called when the user hits Enter on an option."""
        # event.option.prompt is the label we passed in
        label = str(event.option.prompt)
        # You can log here to prove it fires:
        self.dismiss(label)
        event.stop()

    def on_key(self, event: events.Key) -> None:
        """Only handle ESC here; OptionList handles Enter itself."""
        if (event.key or "").lower() == SCREENSHOT_BINDING:
            self.action_take_screenshot()
            event.stop()
            return

        key = (event.key or "").lower()
        if key == "escape":
            event.stop()
            self.dismiss(None)
            return

        if len(key) == 1:
            target = self._hotkey_map.get(key)
            if target:
                event.stop()
                # Highlight the option for visual feedback before dismissing
                if self._olist:
                    try:
                        index = self.options.index(target)
                        self._olist.highlighted = index  # type: ignore[attr-defined]
                    except ValueError:
                        pass
                    except Exception:
                        pass
                self.dismiss(target)

    def _build_hotkey_map(self) -> None:
        """
        Map unique first letters (case-insensitive) to option labels.
        Explicit hotkeys (if provided) take priority; duplicates are removed.
        """

        def register(key: str | None, label: str) -> None:
            if not key:
                return
            key = key.lower()
            if key in duplicates:
                return
            if key in hotkeys and hotkeys[key] != label:
                duplicates.add(key)
                hotkeys.pop(key, None)
            else:
                hotkeys[key] = label

        hotkeys: dict[str, str] = {}
        duplicates: set[str] = set()

        for key, label in self._explicit_hotkeys:
            register(key, label)

        for label in self.options:
            stripped = label.strip()
            inferred = stripped[:1].lower() if stripped else ""
            register(inferred, label)

        for dup in duplicates:
            hotkeys.pop(dup, None)

        self._hotkey_map = hotkeys

    def action_take_screenshot(self) -> None:
        """Delegate the screenshot binding to the main app so it works inside the menu."""
        app = getattr(self, "app", None)
        if app and hasattr(app, "action_take_screenshot"):
            app.action_take_screenshot()


class ChoicePrompt(ModalScreen[Optional[str]]):
    """
    Simple multi-choice prompt.

    Shows a message + numbered options.
    User presses 1/2/3... to select, or ESC to cancel.

    Returns the chosen *string* from `choices`, or None.
    """

    def __init__(self, message: str, choices: List[str]):
        super().__init__()
        self.title_text = " Choose an option"
        self.message = message.strip()
        self.choices = choices

    def compose(self) -> "ComposeResult":
        with Vertical(id="choice_prompt"):
            yield Static(self.title_text, classes="title-class", id="choice_title")

            if self.message:
                yield Static(self.message, id="choice_message")

            # Build numbered list of options
            lines = []
            for i, choice in enumerate(self.choices, start=1):
                lines.append(f"{i}) {choice}")
            choices_text = "\n".join(lines)

            yield Static(
                "Press the number of your choice, or ESC to cancel.",
                id="choice_instructions",
            )
            yield Static(choices_text, id="choice_options")

    def on_key(self, event) -> None:
        key = event.key

        if key == "escape":
            self.dismiss(None)
            return

        # Numeric keys '1', '2', ... map directly to choices
        if key.isdigit():
            idx = int(key)
            if 1 <= idx <= len(self.choices):
                self.dismiss(self.choices[idx - 1])


class ConfirmPrompt(ModalScreen[Optional[bool]]):
    """
    Simple yes/no/escape confirm dialog.

    Returns:
        True  -> user confirmed ("yes")
        False -> user explicitly said "no"
        None  -> user cancelled with ESC
    """

    def __init__(self, message: str):
        super().__init__()
        self.title_text = " Confirm"
        self.message = message.strip()

    def compose(self) -> "ComposeResult":
        with Vertical(id="confirm_prompt"):
            yield Static(self.title_text, classes="title-class", id="confirm_title")

            if self.message:
                yield Static(self.message, id="confirm_message")

            yield Static(
                "Press [bold yellow]Y[/bold yellow] for yes, "
                "[bold yellow]N[/bold yellow] for no, or [bold yellow]ESC[/bold yellow] to cancel.",
                id="confirm_instructions",
            )

    def on_key(self, event) -> None:
        key = event.key.lower()

        if key == "escape":
            self.dismiss(None)
        elif key == "y":
            self.dismiss(True)
        elif key == "n":
            self.dismiss(False)


class TextPrompt(ModalScreen[Optional[str]]):
    """
    Simple text entry prompt.
    Returns the submitted string (stripped) or None if cancelled.
    """

    def __init__(
        self,
        title: str,
        message: str = "",
        initial: str = "",
        placeholder: str = "",
    ):
        super().__init__()
        self._title = title or "Input"
        self._message = message.strip()
        self._initial = initial or ""
        self._placeholder = placeholder
        self._input: Input | None = None

    def compose(self) -> ComposeResult:
        with Vertical(id="text_prompt"):
            yield Static(self._title, classes="title-class", id="text_prompt_title")
            if self._message:
                yield Static(self._message, id="text_prompt_message")

            self._input = Input(
                value=self._initial,
                placeholder=self._placeholder,
                id="text_prompt_input",
            )
            yield self._input

            yield Static(
                "[bold yellow]Enter[/bold yellow] to submit, "
                "[bold yellow]ESC[/bold yellow] to cancel.",
                id="text_prompt_instructions",
            )

    def on_mount(self) -> None:
        self._input = self.query_one("#text_prompt_input", Input)
        self._input.focus()
        if self._initial:
            self._input.cursor_position = len(self._initial)

    @on(Input.Submitted)
    def _on_input_submitted(self, event: Input.Submitted) -> None:
        value = (event.value or "").strip()
        self.dismiss(value or None)
        event.stop()

    def on_key(self, event: events.Key) -> None:
        if event.key in ("left", "right"):
            event.stop()
            return  # Trap nav keys so global bindings don’t fire while dialog is open.
        if event.key == "escape":
            event.stop()
            self.dismiss(None)


class DatetimePrompt(ModalScreen[datetime | None]):
    """
    Prompt for a datetime, live-parsed with dateutil.parser.parse.
    """

    def __init__(
        self,
        message: str,
        subject: str | None = None,
        due: str | None = None,
        default: datetime | None = None,
    ):
        super().__init__()
        self.title_text = " Datetime Entry"
        self.message = message.strip()
        self.default = default or datetime.now()

        self.input: Input | None = None
        self.feedback: Static | None = None
        self.instructions: Static | None = None

    def compose(self) -> ComposeResult:
        default_str = self.default.strftime("%Y-%m-%d %H:%M")

        with Vertical(id="dt_prompt"):
            instructions = [
                "Modify the datetime below if necessary, then press",
                "[bold yellow]ENTER[/bold yellow] to submit or [bold yellow]ESC[/bold yellow] to cancel.",
            ]
            self.instructions = Static("\n".join(instructions), id="dt_instructions")
            self.feedback = Static(f"️↳ {default_str}", id="dt_feedback")
            self.input = Input(value=default_str, id="dt_entry")

            yield Static(self.title_text, classes="title-class", id="dt_title")

            if self.message:
                yield Static(self.message.strip(), id="dt_message")

            yield self.instructions
            yield self.input
            yield self.feedback

    def on_mount(self) -> None:
        """Focus the input and show feedback for the initial value."""
        self.query_one("#dt_entry", Input).focus()
        self._update_feedback(self.input.value)

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

    def on_input_changed(self, event: Input.Changed) -> None:
        """Live-parse as the user types."""
        if event.input.id == "dt_entry":
            self._update_feedback(event.value)

    def on_key(self, event) -> None:
        """Handle Enter and Escape."""
        if event.key == "escape":
            self.dismiss(None)
            event.stop()
        elif event.key == "enter":
            try:
                value = self.input.value.strip()
                parsed = parse(value) if value else self.default
                self.dismiss(parsed)
            except Exception:
                self.dismiss(None)
            finally:
                event.stop()


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

    BINDINGS = [
        (SAVE_BINDING, "save_and_close", "Save"),
        (CANCEL_BINDING, "close", "Back"),
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
                (
                    f"[bold {FOOTER}]{SAVE_LABEL}[/bold {FOOTER}] to save"
                    f" or [bold {FOOTER}]{CANCEL_LABEL}[/bold {FOOTER}] to cancel"
                ),
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
        text_widget = getattr(event, "control", None) or self._text
        if text_widget is not None:
            self._live_parse_and_feedback(final=False, refresh_from_widget=True)
        else:
            self._live_parse_and_feedback(final=False)

        # Optional: stop propagation so nothing else double-handles it
        event.stop()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        # Don't re-parse—just re-render feedback for the new caret position
        self._render_feedback()

    def action_save_and_close(self) -> None:
        ok = self._finalize_and_validate()
        if not ok:
            self.app.notify("Cannot save: fix errors first.", severity="warning")
            return
        self._persist(self.item)
        self.app.notify("Saved.", timeout=0.8)
        self.dismiss({"changed": True, "record_id": self.record_id})

    def action_close(self) -> None:
        self.dismiss(None)  # close without saving

    # ---------- Internals ----------
    def _build_context(self) -> str:
        if self.record_id is None:
            return "New reminder"
        row = self.controller.db_manager.get_record(self.record_id)
        # subj = row[2] or "(untitled)"
        return f"Editing Record {self.record_id}"

    def _finalize_and_validate(self) -> bool:
        """
        Finalize the entry (rrules/jobs/etc) and validate.
        Returns True iff parse_ok after a finalizing parse.
        """
        self._rebuild_item(final=True)
        self.item.finalize_record()
        if not getattr(self.item, "parse_ok", False):
            self._render_feedback()
            return False
        return True

    def _live_parse_and_feedback(
        self, *, final: bool, refresh_from_widget: bool = False
    ) -> None:
        """Non-throwing live parse + feedback for current cursor token."""
        if refresh_from_widget and self._text is not None:
            self.entry_text = self._text.text or ""
        self._rebuild_item(final=final)
        self._render_feedback()

    def _rebuild_item(self, final: bool) -> None:
        """Recreate the Item from current text to avoid stale token positions."""
        self.item = self.ItemCls(self.entry_text, controller=self.controller)
        self.item.final = bool(final)
        self.item.parse_input(self.entry_text)

    def _token_at(self, idx: int) -> Optional[Dict[str, Any]]:
        """Find the token whose [s,e) spans idx; fallback to first incomplete after idx."""
        toks: List[Dict[str, Any]] = getattr(self.item, "relative_tokens", []) or []
        last_before = None
        for t in toks:
            s, e = t.get("s", -1), t.get("e", -1)
            if s <= idx < e:
                return t
            if idx >= e:
                last_before = t
        for t in toks:
            if t.get("incomplete") and t.get("s", 1 << 30) >= idx:
                return t
        return last_before

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

    def _format_schedule_preview(self, tok: dict[str, Any]) -> str | None:
        """Return a weekday-inclusive preview for @s tokens if possible."""
        item = getattr(self, "item", None)
        if not item:
            return None

        raw = (tok.get("token") or "").strip()
        if not raw.lower().startswith("@s"):
            return None

        value = raw[2:].strip()
        if not value:
            return None

        try:
            obj, kind, meta = item.parse_user_dt_for_s(value)
        except Exception:
            return None

        if kind == "error" or obj is None:
            return None

        try:
            return item.fmt_verbose(obj)
        except Exception:
            return None

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
            "t": "Target number/period",
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

        panel = self.query_one("#ed_feedback", Static)  # <— direct, no fallback

        item = getattr(self, "item", None)
        if not item:
            panel.update("")
            return

        # 1) Show validate messages if any.
        if self.item.validate_messages:
            # log_msg(f"{self.item.validate_messages = }")
            panel.update("\n".join(self.item.validate_messages))
            return

        msgs = getattr(item, "messages", None) or []
        if msgs:
            l = []
            if isinstance(msgs, list):
                for msg in msgs:
                    if isinstance(msg, tuple):
                        l.append(msg[1])
                    else:
                        l.append(msg)

            s = "\n".join(l)
            # log_msg(f"{s = }")
            # panel.update("\n".join(msgs))
            panel.update(s)
            return

        last = getattr(item, "last_result", None)
        if last and last[1]:
            panel.update(str(last[1]))
            # return

        # 2) No errors: describe token at cursor (with normalized preview if available).
        idx = self._cursor_abs_index()
        tok = self._token_at(idx)

        if not tok:
            # panel.update("")
            return

        ttype = tok.get("t", "")
        raw = tok.get("token", "").strip()
        k = tok.get("k", "")

        preview = ""
        last = getattr(item, "last_result", None)
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
            if key == "s":
                formatted = self._format_schedule_preview(tok)
                if formatted:
                    preview = f"@s {formatted}"
            panel.update(f"{description} {preview or raw}")
        elif ttype == "&":
            key = tok.get("k", None)
            description = f"{_AMP_DESC.get(key, '')}:" if key else "↳"
            panel.update(f"{description} {preview or raw}")
        else:
            panel.update(f"↳ {raw}{preview}")

    def _persist(self, item) -> None:
        rid = self.controller.db_manager.save_record(item, record_id=self.record_id)
        self.record_id = rid
        if self.item.itemtype in ("~", "^"):
            completion = getattr(item, "completion", None)
            if completion:
                self.controller.db_manager.add_completion(self.record_id, completion)


class DetailsScreen(ModalScreen[None]):
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
        try:
            self.query_one("#details_title", Static).update(self.title_text)
        except NoMatches:
            # Modal no longer renders a dedicated title widget.
            pass

    # ---------- layout ----------
    def compose(self) -> ComposeResult:
        yield Vertical(
            Static("\n".join(self.lines), expand=True, id="details_text"),
            # Static(self.footer_content),
        )
        yield (Static(self.footer_content))
        # yield Footer()

    # ---------- lifecycle ----------
    def on_mount(self) -> None:
        meta = self.app.controller.get_last_details_meta() or {}
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

    def action_show_help(self) -> None:
        # Build the specialized details help
        lines = self._build_help_text().splitlines()
        self.app.push_screen(HelpScreen(lines))

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
        bg_color = getattr(self.app, "list_bg_color", "#373737")
        text_color = getattr(self.app, "list_text_color", None)
        yield Vertical(
            Static(self._title, id="details_title", classes="title-class"),
            ScrollableList(
                self._lines,
                id="help_list",
                bg_color=bg_color,
                text_color=text_color,
            ),
            FooterDisplay(self._footer),
            id="help_layout",
        )

    def on_mount(self):
        self.styles.width = "100%"
        self.styles.height = "100%"
        self.query_one("#help_layout").styles.height = "100%"

        help_list = self.query_one("#help_list", ScrollableList)
        bg_color = getattr(self.app, "list_bg_color", "#373737")
        help_list.set_background_color(bg_color)
        for attr in ("_viewport", "_window", "_scroll_view", "_view", "_content"):
            vp = getattr(help_list, attr, None)
            if vp and hasattr(vp, "styles"):
                vp.styles.background = bg_color
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
        background: transparent;
    }
    """

    def __init__(
        self,
        lines: List[str],
        *,
        match_color: str = MATCH_COLOR,
        bg_color: str | None = None,
        text_color: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._text_color = text_color
        base_style = Style(color=self._text_color) if self._text_color else None
        self.console = Console(style=base_style)
        self.match_color = match_color
        self._bg_color = bg_color or "#373737"
        self.row_bg = Style(bgcolor=self._bg_color)  # ← row background color
        self.styles.background = self._bg_color

        self._base_style = Style(color=self._text_color) if self._text_color else None
        self.lines: List[Text] = [
            Text.from_markup(line, style=self._base_style) for line in lines
        ]
        width = shutil.get_terminal_size().columns - 3
        self.virtual_size = Size(width, len(self.lines))

        self.search_term: Optional[str] = None
        self.matches: List[int] = []
        self.current_match_idx: int = -1

    def on_mount(self):
        self._apply_background_styles()

    def _apply_background_styles(self):
        for attr in ("_viewport", "_window", "_scroll_view", "_view", "_content"):
            vp = getattr(self, attr, None)
            if vp and hasattr(vp, "styles"):
                vp.styles.background = self._bg_color
                if self._text_color:
                    vp.styles.color = self._text_color
                try:
                    vp.refresh()
                except Exception:
                    pass

    def set_background_color(self, color: str) -> None:
        self._bg_color = color
        self.row_bg = Style(bgcolor=color)
        self.styles.background = color
        self._apply_background_styles()

    # ... update_list / search methods unchanged ...

    def update_list(self, new_lines: List[str]) -> None:
        """Replace the list content and refresh."""
        # log_msg(f"{new_lines = }")
        self.lines = [
            Text.from_markup(line, style=self._base_style) for line in new_lines if line
        ]
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

        yield FooterNoticeBar(self.footer_content)

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
            # self.app.controller.afill_by_view["weeks"] = 1
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
        # self.app.controller.afill_by_view["weeks"] = 1

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
        record_id, job_id, datetime_id, instance_ts = rec

        # Controller helper returns title, list-of-lines (fields), and meta
        title, lines, meta = self.app.controller.get_details_for_record(
            record_id, job_id, datetime_id, instance_ts
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
        total_pages = len(self.pages)
        log_msg(f"{self.current_page = }, {total_pages = }")
        if total_pages == 0:
            return None

        # Guard against stale current_page indices (e.g., when pages changed)
        index = max(0, min(self.current_page, total_pages - 1))
        if index != self.current_page:
            self.current_page = index

        try:
            _, tag_map = self.pages[self.current_page]
        except IndexError:
            return None

        return tag_map.get(tag)

    def show_details_for_tag(self, tag: str) -> None:
        app = self.app  # DynamicViewApp
        record = self.get_record_for_tag(tag)
        log_msg(f"{record = }")
        if record:
            record_id, job_id, datetime_id, instance_ts = record

            title, lines, meta = app.controller.get_details_for_record(
                record_id, job_id, datetime_id, instance_ts
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
        yield FooterNoticeBar(self.footer_content)

    def on_mount(self) -> None:
        if self.list_with_details:
            self.list_with_details.update_list(self.lines)
        # Add the initial page indicator after mount
        self.query_one("#scroll_title", Static).update(
            f"{self.title}{self._render_page_indicator()}"
        )


Page = Tuple[List[str], Dict[str, Tuple[str, object]]]


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
    Tagged hierarchy browser for bins:

      • Uses SearchableScreen + ListWithDetails.
      • Shows only the current bin's immediate children (bins listed first) and reminders.
      • Every visible row receives a tag so a–z keys always act on what you see.
      • Breadcrumb header (with digits) lets you jump to ancestors; ESC jumps to root.
      • a–z tags are handled by DynamicViewApp via show_details_for_tag().
      • / search highlights within the current listing.
      • Left/Right change pages when more than 26 rows exist.
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
        self._base_footer = (
            footer_content
            or f"[bold {FOOTER}]?[/bold {FOOTER}] Help "
            f" [bold {FOOTER}]/[/bold {FOOTER}] Search "
            f" [bold {FOOTER}]a-z[/bold {FOOTER}] Open tagged "
        )
        self.footer_content = self._base_footer
        self.list_with_details: Optional[ListWithDetails] = None
        self.tag_map: dict[str, tuple[str, object]] = {}
        self.crumb: list[tuple[int, str]] = []  # [(id, name), ...]
        self._awaiting_bin_action_key: bool = False
        self._selection_kind: str = "bin"  # "bin" or "reminder"

    # ----- Compose -----
    def compose(self) -> ComposeResult:
        # Title: breadcrumb + optional page indicator
        yield Static("", id="scroll_title", classes="title-class", expand=True)

        self.list_with_details = ListWithDetails(id="list")
        # Details handler is the same pattern as other views
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(view_name="bins")
        )
        self.list_with_details.set_details_visibility_callback(
            self._on_details_visibility_change
        )
        yield self.list_with_details

        yield FooterDisplay(self.footer_content)

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
            self._open_bin(int(data))
            return

        # "rem" -> open details
        record_id, job_id = data
        title, lines, meta = self.controller.get_details_for_record(record_id, job_id)
        if self.list_with_details:
            self.list_with_details.show_details(title, lines, meta)

    # ----- Local key handling -----
    def on_key(self, event) -> None:
        k = event.key

        if self._awaiting_bin_action_key:
            self._awaiting_bin_action_key = False
            self._handle_bin_action_shortcut(k)
            event.stop()
            return

        if k == "comma":
            self._awaiting_bin_action_key = True
            self._notify("Bin action shortcut: press a/r/m/d.", timeout=2)
            event.stop()
            return

        # ESC -> jump to root (same behavior as BinView)
        if k == "escape":
            root_id = getattr(self.controller, "root_id", None)
            if root_id is not None:
                self.bin_id = root_id
                self.refresh_hierarchy()
                event.stop()
                return

        if k == "enter":
            if self._current_bin_supports_menu():
                self._prompt_bin_actions(self.bin_id)
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
        self._selection_kind = "bin"
        self._refresh_page()

    def _render_bin_row(
        self, child: ChildBinRow, tag: str, *, parent_name: str | None = None
    ) -> str:
        counts: list[str] = []
        if child.child_ct:
            noun = "bin" if child.child_ct == 1 else "bins"
            counts.append(f"{child.child_ct} {noun}")
        if child.rem_ct:
            noun = "reminder" if child.rem_ct == 1 else "reminders"
            counts.append(f"{child.rem_ct} {noun}")
        counts_text = (
            f" [{DIM_STYLE}]({', '.join(counts)})[/{DIM_STYLE}]" if counts else ""
        )
        display_name = child.name
        if parent_name and ":" in child.name:
            prefix, suffix = child.name.split(":", 1)
            if prefix == parent_name:
                display_name = suffix

        name_color = TYPE_TO_COLOR["b"]
        tag_style = DIM_STYLE
        return (
            f"  [{tag_style}]{tag}[/{tag_style}] "
            f"[{name_color}]{display_name}[/ {name_color}]"
            f"{counts_text}"
        ).rstrip()

    def _render_reminder_row(self, r: ReminderRow, tag: str) -> str:
        tclr = TYPE_TO_COLOR[r.itemtype]
        tag_style = DIM_STYLE
        return f"  [{tag_style}]{tag}[/{tag_style}] [{tclr}]{r.itemtype} {r.subject}[/{tclr}]"

    def _refresh_page(self) -> None:
        rows, tag_map = self.pages[self.current_page] if self.pages else ([], {})
        self.tag_map = tag_map

        if self.list_with_details:
            self.list_with_details.update_list(rows)
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()

        self._refresh_header()
        self._refresh_footer_text()

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
        Build pages limited to the current bin's immediate children and reminders.
        """
        # 1) Summary + breadcrumb
        children, reminders, crumb = self.controller.get_bin_summary(
            self.bin_id, filter_text=None
        )
        self.crumb = crumb

        # 2) Crumb text: ancestors numbered, last (current) unnumbered
        if crumb:
            parts: list[str] = []
            for i, (_bid, name) in enumerate(crumb):
                if i < len(crumb) - 1:
                    parts.append(
                        f"[{DIM_STYLE}]{i}[/{DIM_STYLE}] [{TYPE_TO_COLOR['b']}]{name}[/{TYPE_TO_COLOR['b']}]"
                    )
                else:
                    parts.append(
                        f"[bold {TYPE_TO_COLOR['B']}]{name}[/bold {TYPE_TO_COLOR['B']}]"
                    )
                    # parts.append(f"[bold red]{name}[/bold red]")
            crumb_txt = " / ".join(parts)
        else:
            crumb_txt = "root"

        # 3) Build taggable items: children first, then reminders
        taggable: list[tuple[str, object]] = []
        for ch in children:
            taggable.append(("bin", ch.bin_id))
        for r in reminders:
            taggable.append(("rem", (r.record_id, None)))  # job_id=None for now

        # Map reminders by ID for label rendering
        child_by_id: dict[int, ChildBinRow] = {c.bin_id: c for c in children}
        rem_by_id: dict[int, ReminderRow] = {r.record_id: r for r in reminders}

        pages: list[tuple[list[str], dict[str, tuple[str, object]]]] = []

        if not taggable:
            rows = [
                crumb_txt,
                "",
                f"[{DIM_STYLE}]No child bins or reminders.[/{DIM_STYLE}]",
            ]
            pages.append((rows, {}))
            return pages, crumb_txt  # title = crumb_txt

        total = len(taggable)
        num_pages = (total + 25) // 26  # 26 tags per page

        parent_name = self._current_bin_name()

        for page_index in range(num_pages):
            start = page_index * 26
            end = min(start + 26, total)
            page_items = taggable[start:end]

            page_tag_map: dict[str, tuple[str, object]] = {}

            # Assign tags to taggable items for this page
            for i, (kind, data) in enumerate(page_items):
                tag = TAGS[i]
                if kind == "bin":
                    page_tag_map[tag] = ("bin", int(data))
                else:
                    record_id, job_id = data
                    page_tag_map[tag] = ("rem", (record_id, job_id))

            rows: list[str] = [crumb_txt]
            added_bin_gap = False
            added_rem_gap = False

            for i, (kind, data) in enumerate(page_items):
                tag = TAGS[i]
                if kind == "bin":
                    child = child_by_id.get(int(data))
                    if not child:
                        continue
                    if not added_bin_gap:
                        rows.append("")
                        added_bin_gap = True
                    rows.append(
                        self._render_bin_row(child, tag, parent_name=parent_name)
                    )
                else:
                    record_id, job_id = data
                    reminder = rem_by_id.get(record_id)
                    if not reminder:
                        continue
                    if not added_rem_gap:
                        if rows and rows[-1]:
                            rows.append("")
                        added_rem_gap = True
                    rows.append(self._render_reminder_row(reminder, tag))

            pages.append((rows, page_tag_map))

        # Title is just the crumb text; page indicator is added in _refresh_header
        return pages, crumb_txt

    def _prompt_bin_actions(self, target_bin_id: int) -> None:
        """Show available operations for a tagged bin."""
        if not self._bin_supports_menu(target_bin_id):
            return
        try:
            ctx = self._get_bin_action_context(target_bin_id)
        except Exception as exc:
            self._notify(f"Failed to load bin: {exc}", severity="error")
            return

        bin_name = ctx["name"]
        action_options: list[tuple[str, str]] = []
        if not ctx["is_root"]:
            action_options.append(("Open bin", "o"))
        if ctx["allow_children"]:
            action_options.append(("Add child", "a"))
        if not ctx["is_protected"]:
            action_options.extend(
                [
                    ("Rename bin", "r"),
                    ("Move bin", "m"),
                    ("Delete bin", "d"),
                ]
            )

        just_open = len(action_options) == 1 and action_options[0][0] == "Open bin"
        if just_open:
            self._open_bin(target_bin_id)
            return

        options: list[Union[str, tuple[str, str]]] = action_options
        message = (
            f"[{TYPE_TO_COLOR['b']}]{bin_name}[/ {TYPE_TO_COLOR['b']}]\n"
            "Choose an action:"
        )

        def _after(choice: str | None) -> None:
            if not choice:
                return
            if choice == "Open bin":
                self._open_bin(target_bin_id)
            elif choice == "Add child":
                self._prompt_add_child(target_bin_id, bin_name)
            elif choice == "Rename bin":
                self._prompt_rename_bin(target_bin_id, bin_name)
            elif choice == "Move bin":
                self._prompt_move_bin(target_bin_id, bin_name)
            elif choice == "Delete bin":
                self._prompt_delete_bin(target_bin_id, bin_name)

        self.app.push_screen(OptionPrompt(message, options), callback=_after)

    def _open_bin(self, bin_id: int) -> None:
        self.bin_id = bin_id
        self.refresh_hierarchy()
        self._set_selection_kind("bin")

    def _set_selection_kind(self, kind: str) -> None:
        if kind == self._selection_kind:
            return
        self._selection_kind = kind
        self._refresh_footer_text()

    def _current_bin_name(self) -> str:
        if self.crumb:
            return self.crumb[-1][1]
        return self.controller.get_bin_name(self.bin_id)

    def _is_root_bin(self, bin_id: int) -> bool:
        try:
            root_id = self.controller.root_id
        except Exception:
            root_id = None
        return root_id is not None and bin_id == root_id

    def _get_bin_action_context(self, bin_id: int) -> dict[str, object]:
        name = self.controller.get_bin_name(bin_id)
        try:
            is_protected = self.controller.is_protected_bin(bin_id)
        except Exception:
            is_protected = False
        return {
            "name": name,
            "is_protected": is_protected,
            "is_root": self._is_root_bin(bin_id),
            "allow_children": True,
        }

    def _handle_bin_action_shortcut(self, key: str) -> None:
        action = (key or "").lower()
        try:
            ctx = self._get_bin_action_context(self.bin_id)
        except Exception as exc:
            self._notify(f"Bin action unavailable: {exc}", severity="error")
            return

        name = ctx["name"]
        if action == "a":
            if not ctx["allow_children"]:
                self._notify("Cannot add children here.", severity="warning")
                return
            self._prompt_add_child(self.bin_id, name)
        elif action == "r":
            if ctx["is_protected"]:
                self._notify("System bins cannot be renamed.", severity="warning")
                return
            self._prompt_rename_bin(self.bin_id, name)
        elif action == "m":
            if ctx["is_protected"]:
                self._notify("System bins cannot be moved.", severity="warning")
                return
            self._prompt_move_bin(self.bin_id, name)
        elif action == "d":
            if ctx["is_protected"]:
                self._notify("System bins cannot be deleted.", severity="warning")
                return
            self._prompt_delete_bin(self.bin_id, name)
        elif action:
            self._notify(f"No bin action bound to '{action}'.", severity="warning")

    def _on_details_visibility_change(self, visible: bool) -> None:
        self._set_selection_kind("reminder" if visible else "bin")

    def _bin_supports_menu(self, bin_id: int) -> bool:
        try:
            if self._is_root_bin(bin_id):
                return True
            return not self.controller.is_protected_bin(bin_id)
        except Exception:
            return False

    def _current_bin_supports_menu(self) -> bool:
        return self._bin_supports_menu(self.bin_id)

    def _refresh_footer_text(self) -> None:
        show_bin_hint = (
            self._selection_kind != "reminder" and self._current_bin_supports_menu()
        )
        enter_hint = (
            f"  [bold {FOOTER}]Enter[/bold {FOOTER}] Bin menu" if show_bin_hint else ""
        )
        text = f"{self._base_footer}{enter_hint}"
        self.footer_content = text
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update(text)
        except Exception:
            pass

    def _prompt_add_child(self, parent_id: int, parent_name: str) -> None:
        message = (
            f"Create a child under [{TYPE_TO_COLOR['b']}]{parent_name}"
            f"[/ {TYPE_TO_COLOR['b']}]."
        )

        def _after(result: str | None) -> None:
            if not result:
                return
            try:
                self.controller.create_bin(result, parent_id)
            except Exception as exc:
                self._notify(str(exc), severity="error")
                return
            self._notify(f"Added bin '{result}'.")
            self.refresh_hierarchy()

        self.app.push_screen(
            TextPrompt(
                "Add Bin",
                message=message,
                placeholder="New bin name",
            ),
            callback=_after,
        )

    def _prompt_rename_bin(self, bin_id: int, current_name: str) -> None:
        def _after(result: str | None) -> None:
            if not result or result == current_name:
                return
            try:
                self.controller.rename_bin(bin_id, result)
            except Exception as exc:
                self._notify(str(exc), severity="error")
                return
            self._notify("Bin renamed.")
            self.refresh_hierarchy()

        self.app.push_screen(
            TextPrompt(
                "Rename Bin",
                message="Enter a new name:",
                initial=current_name,
            ),
            callback=_after,
        )

    def _prompt_move_bin(self, bin_id: int, bin_name: str) -> None:
        parent = self.controller.get_parent_bin(bin_id)
        initial_parent = parent["name"] if parent else "root"
        message = (
            f"Move [{TYPE_TO_COLOR['b']}]{bin_name}[/ {TYPE_TO_COLOR['b']}] "
            "under which parent?\n"
            "Enter an existing bin name (case-insensitive)."
        )

        def _after(result: str | None) -> None:
            if not result:
                return
            new_parent_id = self.controller.find_bin_id_by_name(result)
            if new_parent_id is None:
                self._notify(f"No bin named '{result}'.", severity="warning")
                return
            try:
                self.controller.move_bin_under(bin_id, new_parent_id)
            except Exception as exc:
                self._notify(str(exc), severity="error")
                return
            self._notify("Bin moved.")
            self.refresh_hierarchy()

        self.app.push_screen(
            TextPrompt(
                "Move Bin",
                message=message,
                initial=initial_parent,
                placeholder="Parent bin name",
            ),
            callback=_after,
        )

    def _prompt_delete_bin(self, bin_id: int, bin_name: str) -> None:
        message = (
            f"Delete [{TYPE_TO_COLOR['b']}]{bin_name}"
            f"[/ {TYPE_TO_COLOR['b']}]?\n"
            "Empty bins are removed permanently; others move under 'unlinked'."
        )

        def _after(result: Optional[bool]) -> None:
            if not result:
                return
            try:
                outcome = self.controller.delete_bin(bin_id)
            except Exception as exc:
                self._notify(str(exc), severity="error")
                return
            if outcome == "purged":
                self._notify("Bin deleted.")
            else:
                self._notify("Bin moved to 'unlinked'.")
            self.refresh_hierarchy()

        self.app.push_screen(ConfirmPrompt(message), callback=_after)

    def _notify(self, message: str, *, severity: str = "info", timeout: float = 1.5):
        app = getattr(self, "app", None)
        if app and hasattr(app, "notify"):
            app.notify(message, severity=severity, timeout=timeout)


class QueryScreen(SearchableScreen, SafeScreen):
    """Interactive query view with history and paged results."""

    def __init__(self, controller):
        super().__init__()
        self.controller = controller
        self.query_input: Input | None = None
        self.status_label: Static | None = None
        self.list_with_details: ListWithDetails | None = None
        self.history: list[str] = []
        self.history_index: int = 0
        self.pages: list[tuple[list[str], dict[str, object]]] = []
        self.current_page: int = 0
        self.matches: list[QueryMatch] = []
        self._footer_default = (
            f"[bold {FOOTER}]?[/bold {FOOTER}] Help  "
            f"[bold {FOOTER}]Enter[/bold {FOOTER}] Run query  "
            f"[bold {FOOTER}]Tab[/bold {FOOTER}] query ↔ list"
        )
        self._footer_list_only = (
            f"[bold {FOOTER}]?[/bold {FOOTER}] Help  "
            f"[bold {FOOTER}]Tab[/bold {FOOTER}] query ↔ list  "
            f"[bold {FOOTER}]Esc[/bold {FOOTER}] close details"
        )
        self.footer_content = self._footer_default

    def compose(self) -> ComposeResult:
        yield Static("Query", id="query_title", classes="title-class")
        self.query_input = Input(
            placeholder="includes subject waldo",
            id="query_input",
        )
        yield self.query_input
        self.status_label = Static(
            "Enter a query",
            id="query_status",
        )
        yield self.status_label

        self.list_with_details = ListWithDetails(id="query_results")
        self.list_with_details.set_detail_key_handler(
            self.app.make_detail_key_handler(view_name="query")
        )
        self.list_with_details.set_details_visibility_callback(
            self._on_details_visibility_change
        )
        yield self.list_with_details

        yield FooterDisplay(self.footer_content)

    def after_mount(self) -> None:
        self._focus_query_input()
        self._set_status("Enter a query", "info")
        self._rebuild_pages([])

    def show_details_for_tag(self, tag: str) -> None:
        if not self.pages:
            return
        _, tag_map = self.pages[self.current_page]
        meta = tag_map.get(tag)
        if not meta:
            return
        record_id = meta.get("record_id")
        if not record_id:
            return
        job_id = meta.get("job_id")
        try:
            title, lines, details_meta = self.controller.get_details_for_record(
                record_id, job_id
            )
        except Exception as exc:
            self._set_status(f"Failed to load record {record_id}: {exc}", "error")
            return
        if self.list_with_details:
            self.list_with_details.show_details(title, lines, details_meta)
        self._set_status(f"Showing record {record_id}", "info")

    def _focus_query_input(self) -> None:
        if self.query_input:
            self.query_input.focus()

    def _focus_results_list(self) -> None:
        if self.list_with_details:
            try:
                self.list_with_details.focus()
            except Exception:
                pass
        if self.query_input and self.query_input.has_focus:
            try:
                self.query_input.blur()
            except Exception:
                pass

    def has_next_page(self) -> bool:
        return self.current_page < len(self.pages) - 1

    def has_prev_page(self) -> bool:
        return self.current_page > 0

    def next_page(self) -> None:
        if self.has_next_page():
            self.current_page += 1
            self._refresh_page()

    def previous_page(self) -> None:
        if self.has_prev_page():
            self.current_page -= 1
            self._refresh_page()

    def _refresh_page(self) -> None:
        rows, tag_map = self.pages[self.current_page] if self.pages else ([], {})
        if self.list_with_details:
            self.list_with_details.update_list(rows)
            self.list_with_details.set_meta_map(tag_map)
            if self.list_with_details.has_details_open():
                self.list_with_details.hide_details()
        self.controller.list_tag_to_id.setdefault("query", {})
        self.controller.list_tag_to_id["query"] = tag_map
        self._update_match_status()

    def _rebuild_pages(self, matches: list[QueryMatch]) -> None:
        self.matches = matches
        pages: list[tuple[list[str], dict[str, object]]] = []
        rows: list[str] = []
        tag_map: dict[str, dict[str, object]] = {}

        for idx, match in enumerate(matches):
            if idx % len(TAGS) == 0 and rows:
                pages.append((rows, tag_map))
                rows = []
                tag_map = {}
            tag = TAGS[idx % len(TAGS)]
            subject = match.subject or "(untitled)"
            rows.append(
                f" [{DIM_STYLE}]{tag}[/{DIM_STYLE}] {match.itemtype} {subject} (id {match.record_id})"
            )
            tag_map[tag] = {
                "record_id": match.record_id,
                "job_id": None,
                "itemtype": match.itemtype,
                "subject": subject,
            }

        if rows or tag_map:
            pages.append((rows, tag_map))

        if not pages:
            pages = [([], {})]

        self.pages = pages
        self.current_page = 0
        self._refresh_page()

    def _set_status(self, message: str, severity: str = "info") -> None:
        palette = getattr(self.app, "status_colors", None)
        if palette is None:
            palette = {"info": "white", "warning": "yellow", "error": "red"}
        color = palette.get(severity, "white")
        if self.status_label:
            self.status_label.update(f"[{color}]{message}[/]")

    def _run_query(self, text: str) -> bool:
        query = (text or "").strip()
        if not query:
            self._set_status("Enter a query.", "warning")
            return False
        try:
            response = self.controller.run_query(query)
        except QueryError as exc:
            self._set_status(str(exc), "error")
            return False

        if not self.history or self.history[-1] != query:
            self.history.append(query)
        self.history_index = len(self.history)

        if response.info_id is not None:
            try:
                title, lines, meta = self.controller.get_details_for_record(
                    response.info_id
                )
            except Exception:
                self._set_status(
                    f"No record found with id {response.info_id}.", "error"
                )
                return
            if self.list_with_details:
                self.list_with_details.show_details(title, lines, meta)
            self._set_status(f"Opened record {response.info_id}.", "info")
            return False

        matches = response.matches
        if not matches:
            self._set_status("No results.", "warning")
            self._rebuild_pages(matches)
            return True

        self._rebuild_pages(matches)
        self._update_match_status()
        return True

    def _update_match_status(self) -> None:
        if not self.matches:
            return
        total_pages = max(1, len(self.pages))
        indicator = (
            f" ({self.current_page + 1}/{total_pages})" if total_pages > 1 else ""
        )
        self._set_status(f"Matching ({len(self.matches)}){indicator}:", "info")

    @on(Input.Submitted)
    def _handle_query_submit(self, event: Input.Submitted) -> None:
        if event.input != self.query_input:
            return
        if self._run_query(event.value or ""):
            self._focus_results_list()
        event.stop()

    def _history_previous(self) -> None:
        if not self.history:
            return
        self.history_index = max(0, self.history_index - 1)
        self._apply_history_value()

    def _history_next(self) -> None:
        if not self.history:
            return
        if self.history_index < len(self.history) - 1:
            self.history_index += 1
            self._apply_history_value()
        else:
            self.history_index = len(self.history)
            if self.query_input:
                self.query_input.value = ""

    def _apply_history_value(self) -> None:
        if self.query_input and self.history:
            idx = min(self.history_index, len(self.history) - 1)
            if 0 <= idx < len(self.history):
                self.query_input.value = self.history[idx]

    def on_key(self, event) -> None:
        if event.key == "escape":
            if self.list_with_details and self.list_with_details.has_details_open():
                self.list_with_details.hide_details()
                event.stop()
                return
        if (
            event.key in ("up", "down")
            and self.query_input
            and self.query_input.has_focus
        ):
            if event.key == "up":
                self._history_previous()
            else:
                self._history_next()
            event.stop()
            return
        parent = super()
        if hasattr(parent, "on_key"):
            return parent.on_key(event)
        return None

    def _on_details_visibility_change(self, visible: bool) -> None:
        new_text = self._footer_list_only if visible else self._footer_default
        if self.footer_content == new_text:
            return
        self.footer_content = new_text
        try:
            footer = self.query_one("#custom_footer", Static)
            footer.update(new_text)
        except Exception:
            pass


class DynamicViewApp(App):
    """A dynamic app that supports temporary and permanent view changes."""

    CSS_PATH = None
    VIEW_REFRESHERS = {
        "weeks": "action_show_weeks",
        "agenda": "action_show_agenda",
        "goals": "action_show_goals",
        "query": "action_show_query",
        "modified": "action_show_modified",
        "year": "action_show_year",
        # ...
    }

    digit_buffer = reactive([])
    # afill = 1
    search_term = reactive("")

    BINDINGS = [
        # glofitness bal
        # (".fitness ", "center_week", ""),
        ("space", "current_period", ""),
        ("shift+left", "previous_period", ""),
        ("shift+right", "next_period", ""),
        (SCREENSHOT_BINDING, "take_screenshot", "Take Screenshot"),
        ("escape", "close_details", "Close details"),
        ("R", "show_alerts", "Show Alerts"),
        ("A", "show_agenda", "Show Agenda"),
        ("G", "show_goals", "Goals"),
        ("B", "show_bins", "Bins"),
        ("Q", "show_query", "Query"),
        ("C", "show_completions", "Completions"),
        ("L", "show_last", "Show Last"),
        ("M", "show_modified", "Show Modified"),
        ("N", "show_next", "Show Next"),
        ("T", "show_tags", "Show Tags"),
        ("F", "show_find", "Find"),
        ("W", "show_weeks", "Weeks"),
        ("J", "jump_to_week", "Jump to date"),
        ("Y", "show_year", "Year"),
        ("?", "show_help", "Help"),
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+n", "new_reminder", "Add new reminder"),
        ("+", "new_reminder", "Add new reminder"),
        ("ctrl+r", "detail_repetitions", "Show Repetitions"),
        ("/", "start_search", "Search"),
        (">", "next_match", "Next Match"),
        ("<", "previous_match", "Previous Match"),
        ("ctrl+z", "copy_search", "Copy Search"),
        ("ctrl+u", "check_updates", "Check updates"),
        ("ctrl-b", "show_bin", "Bin"),
    ]

    def __init__(self, controller) -> None:
        theme = getattr(getattr(controller, "env", None), "config", None)
        theme = getattr(getattr(theme, "ui", None), "theme", "dark")
        self._theme = theme if theme in {"dark", "light"} else "dark"
        palette = {
            "dark": {
                "list_bg": "#373737",
                "list_text": "white",
                "footer": FOOTER,
                "title": TITLE_COLOR,
            },
            "light": {
                "list_bg": "#fdfdfd",
                "list_text": "#1f1f1f",
                "footer": FOOTER_LIGHT,
                "title": "#204060",
            },
        }
        colors = palette[self._theme]
        self.list_bg_color = colors["list_bg"]
        self.list_text_color = colors["list_text"]
        self.footer_color = colors["footer"]
        self.title_color = colors["title"]
        self.update_indicator_text = ""
        if self._theme == "light":
            self.status_colors = {
                "info": "#1f1f1f",
                "warning": "#a65c00",
                "error": "#b00020",
            }
        else:
            self.status_colors = {
                "info": "white",
                "warning": "yellow",
                "error": "red",
            }
        self.CSS_PATH = f"view_{self._theme}.css"
        super().__init__()
        self.controller = controller
        # self._apply_update_indicator(check_update_available(VERSION))
        self._update_footer_color()
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        self._week_state_before_editor: tuple[datetime, tuple[int, int]] | None = None
        self.title = ""
        self.view_mode = "list"
        self.view = "weeks"
        self.saved_lines = []
        self.afill = 1
        self.leader_mode = False
        footer_color = getattr(self, "footer_color", FOOTER)
        self.details_footer = (
            f"[bold {footer_color}]?[/bold {footer_color}] Help "
            f"[bold {footer_color}]/[/bold {footer_color}] Search  "
            f"[bold {footer_color}]Enter[/bold {footer_color}] Reminder menu "
        )
        self.details_drawer: DetailsDrawer | None = None
        self.year_offset = 0
        self.today: date | None = None
        self.run_daily_tasks(refresh=False)
        self._last_inbox_check = datetime.min
        self._current_command_task: asyncio.Task | None = None

    def _update_footer_color(self) -> None:
        global FOOTER, DIM_STYLE
        FOOTER = self.footer_color
        DIM_STYLE = DIM_STYLE_LIGHT if self._theme == "light" else DIM_STYLE_DARK

    def _apply_update_indicator(self, has_update: bool) -> None:
        color = getattr(self, "footer_color", FOOTER)
        self.update_indicator_text = (
            f" [bold {color}]\U0001d566[/bold {color}]" if has_update else ""
        )
        self._refresh_footer_indicator()

    def _refresh_footer_indicator(self) -> None:
        try:
            screen = self.screen
        except ScreenStackError:
            return
        if screen is None:
            return
        try:
            for bar in screen.query(FooterNoticeBar):
                bar.refresh_indicator()
        except ScreenStackError:
            return

    async def on_mount(self):
        # open default screen
        self.action_show_agenda()

        # your alert timers as-is
        now = datetime.now()
        seconds_to_next = (6 - (now.second % 6)) % 6
        await asyncio.sleep(seconds_to_next)
        self.set_interval(6, self.check_alerts)
        # Fallback guard: once per minute ensure we notice a missed day rollover.
        self.set_interval(60, self._daily_rollover_guard)

    async def action_check_updates(self) -> None:
        """Manually check PyPI for a newer release and refresh the footer indicator."""
        loop = asyncio.get_running_loop()

        def _check():
            return check_update_available(VERSION)

        self.notify("Checking for updates…", severity="info", timeout=1.5)
        has_update = await loop.run_in_executor(None, _check)
        self._apply_update_indicator(has_update)
        if has_update:
            self.notify("Update available on PyPI ✔︎", severity="warning", timeout=3.0)
        else:
            self.notify(
                f"The installed version, {VERSION}, is the latest available.",
                severity="info",
                timeout=3.0,
            )

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

    def _screen_show_details(
        self,
        title: str,
        lines: list[str],
        meta: dict | None = None,
        *,
        push_history: bool = False,
    ) -> None:
        screen = self.screen
        log_msg("showing details")
        list_widget = getattr(screen, "list_with_details", None)
        if list_widget:
            list_widget.show_details(title, lines, meta, push_history=push_history)
            return

        if hasattr(screen, "show_details"):
            screen.show_details(title, lines)
            return

        self.push_screen(DetailsScreen([title] + lines))

    def open_delete_prompt(
        self,
        *,
        record_id: int,
        job_id: int | None,
        subject: str,
        itemtype: str,
        instance_ts: str | None,
        is_repeating: bool,
    ) -> None:
        """Open an OptionPrompt to choose how/what to delete for a record."""
        ctrl = self.controller

        # Build options + message depending on whether this is a repeating item
        if is_repeating and instance_ts and itemtype in "~*":
            options = [
                ("Just this instance", "j"),
                ("This and all subsequent instances", "a"),
                ("The reminder itself", "t"),
            ]
            msg = (
                f"Delete [{LIGHT_SKY_BLUE}]{subject}[/{LIGHT_SKY_BLUE}]?\n\n"
                "Choose what to delete:"
            )
        else:
            options = [("Delete record", "d")]
            msg = (
                f"Delete [{LIGHT_SKY_BLUE}]{subject}[/{LIGHT_SKY_BLUE}]?\n\n"
                "This cannot be undone."
            )

        def _after_choice(choice: str | None) -> None:
            log_msg(f"delete prompt returned {choice = }")

            if not choice:
                return

            changed = False

            if choice == "Delete record":
                # Entire reminder (and all jobs, if any)
                ctrl.delete_record(record_id)
                changed = True

            elif choice == "Just this instance":
                if instance_ts:
                    ctrl.delete_instance(
                        record_id,
                        instance_text=instance_ts,
                    )
                    changed = True

            elif choice == "This and all subsequent instances":
                if instance_ts:
                    ctrl.delete_this_and_future(
                        record_id,
                        instance_text=instance_ts,
                    )
                    changed = True

            elif choice == "The reminder itself":
                ctrl.delete_record(record_id)
                changed = True

            if changed:
                # 1) Close details so there’s no stale panel
                if hasattr(self, "_close_details_if_open"):
                    self._close_details_if_open()

                # 2) Refresh the current view (weeks/agenda/next/etc.)
                if hasattr(self, "refresh_view"):
                    self.refresh_view()

        # Push the modal with a callback; no async/await here
        self.push_screen(OptionPrompt(msg, options), callback=_after_choice)

    def make_detail_key_handler(self, *, view_name: str, week_provider=None):
        ctrl = self.controller
        app = self

        def handler(key: str, meta: dict) -> None:  # chord-aware, sync
            record_id = meta.get("record_id")
            job_id = meta.get("job_id")
            first = meta.get("first")
            second = meta.get("second")
            itemtype = meta.get("itemtype")
            subject = meta.get("subject")
            # instance-aware info
            instance_ts = meta.get("instance_ts")
            datetime_id = meta.get("datetime_id")
            record_payload = meta.get("record") or {}
            tokens_raw = record_payload.get("tokens")
            tokens_list: list[dict] = []
            if isinstance(tokens_raw, str):
                try:
                    tokens_list = json.loads(tokens_raw)
                except Exception:
                    tokens_list = []
            elif isinstance(tokens_raw, list):
                tokens_list = tokens_raw

            def _has_token(token_type: str, key: str) -> bool:
                return any(
                    isinstance(tok, dict)
                    and tok.get("t") == token_type
                    and tok.get("k") == key
                    for tok in tokens_list
                )

            has_links = _has_token("@", "g")
            has_rrule = bool(meta.get("rruleset"))

            if not record_id:
                return

            def finish_item() -> None:
                if itemtype not in "~^!":
                    return
                job = f" {job_id}" if job_id else ""
                id_part = f"({record_id}{job})"
                due = (
                    f"\nDue: [{LIGHT_SKY_BLUE}]{fmt_user(first)}[/{LIGHT_SKY_BLUE}]"
                    if first
                    else ""
                )
                msg = (
                    f"Finished datetime\n"
                    f"For: [{LIGHT_SKY_BLUE}]{subject} {id_part}[/{LIGHT_SKY_BLUE}]{due}"
                )

                def _after_dt(dt: datetime | None) -> None:
                    if dt:
                        ctrl.finish_task(record_id, job_id=job_id, when=dt)
                        if hasattr(app, "refresh_view"):
                            app.refresh_view()

                app.prompt_datetime_with_callback(msg, _after_dt)

            def edit_item() -> None:
                seed_text = ctrl.get_entry_from_record(record_id)

                # Close/hide details before opening the editor
                try:
                    scr = app.screen
                    if (
                        hasattr(scr, "list_with_details")
                        and scr.list_with_details.has_details_open()
                    ):
                        if hasattr(scr.list_with_details, "hide_details"):
                            scr.list_with_details.hide_details()
                except Exception as e:
                    log_msg(f"Error while hiding details before edit: {e}")

                app._remember_week_context()
                app.push_screen(
                    EditorScreen(ctrl, record_id, seed_text=seed_text),
                    callback=self._after_edit,
                )

            def clone_item() -> None:
                seed_text = ctrl.get_entry_from_record(record_id)
                app._remember_week_context()
                app.push_screen(
                    EditorScreen(ctrl, None, seed_text=seed_text),
                    callback=self._after_edit,
                )

            def delete_item() -> None:
                is_repeating = second is not None
                app.open_delete_prompt(
                    record_id=record_id,
                    job_id=job_id,
                    subject=subject,
                    itemtype=itemtype,
                    instance_ts=instance_ts,
                    is_repeating=is_repeating,
                )

            def schedule_new_instance() -> None:
                def _after_dt(dt: datetime | None) -> None:
                    if dt:
                        ctrl.schedule_new(record_id, job_id=job_id, when=dt)
                        if hasattr(app, "refresh_view"):
                            app.refresh_view()

                app.prompt_datetime_with_callback("Schedule when?", _after_dt)

            def reschedule_item() -> None:
                if instance_ts:
                    msg = (
                        f"Reschedule instance for "
                        f"[{LIGHT_SKY_BLUE}]{subject}[/{LIGHT_SKY_BLUE}] "
                        f"from {instance_ts} to?"
                    )

                    def _after_dt(dt: datetime | None) -> None:
                        if dt:
                            ctrl.reschedule_instance(
                                record_id,
                                # job_id=job_id,
                                old_instance_text=instance_ts,
                                new_when=dt,
                            )
                            if hasattr(app, "refresh_view"):
                                app.refresh_view()

                    app.prompt_datetime_with_callback(msg, _after_dt)

                else:
                    # fallback: older coarse reschedule
                    def _after_dt(dt: datetime | None) -> None:
                        if dt:
                            yrwk = week_provider() if week_provider else None
                            ctrl.reschedule(
                                record_id, when=dt, context=view_name, yrwk=yrwk
                            )

                    app.prompt_datetime_with_callback("Reschedule to?", _after_dt)

            def goto_item() -> None:
                self.action_open_with_default(record_id)

            def touch_item() -> None:
                ctrl.touch_item(record_id)
                if hasattr(app, "notify"):
                    app.notify("Reminder touched ✓", severity="info", timeout=1.2)
                if hasattr(app, "refresh_view"):
                    app.refresh_view()

            def toggle_pin() -> None:
                ctrl.toggle_pinned(record_id)
                if hasattr(app, "_reopen_details"):
                    app._reopen_details(tag_meta=meta)

            def show_completions() -> None:
                title, lines = ctrl.get_record_completions(record_id)
                if hasattr(app, "_screen_show_details"):
                    app._screen_show_details(title, lines, meta, push_history=True)

            def show_repetitions() -> None:
                title, lines = ctrl.get_record_repetitions(record_id)
                if hasattr(app, "_screen_show_details"):
                    app._screen_show_details(title, lines, meta, push_history=True)

            def copy_details_to_clipboard() -> None:
                scr = getattr(app, "screen", None)
                lwd = getattr(scr, "list_with_details", None)
                if not lwd or not getattr(lwd, "_current_details", None):
                    if hasattr(app, "notify"):
                        app.notify(
                            "No details to copy", severity="warning", timeout=1.5
                        )
                    return
                title, lines, meta_dict = lwd._current_details
                ok, message = lwd._copy_details_to_clipboard(
                    title, lines, meta_dict or {}
                )
                if hasattr(app, "notify"):
                    if ok:
                        app.notify(
                            "Details copied to clipboard ✓",
                            severity="info",
                            timeout=1.2,
                        )
                    elif message:
                        app.notify(message, severity="warning", timeout=2.0)

            def show_action_menu() -> None:
                options: list[str] = []
                callbacks: dict[str, Callable[[], None]] = {}

                def add_option(
                    label: str,
                    func: Callable[[], None],
                    *,
                    enabled: bool = True,
                    hotkey: str | None = None,
                ) -> None:
                    if not enabled:
                        return
                    if hotkey:
                        options.append((label, hotkey))
                    else:
                        options.append(label)
                    callbacks[label] = func

                add_option("Finish", finish_item, enabled=itemtype in "~^!", hotkey="f")
                add_option("Edit", edit_item, enabled=True, hotkey="e")
                add_option("Clone", clone_item, enabled=True, hotkey="c")
                add_option("Delete …", delete_item, enabled=True, hotkey="d")
                add_option(
                    "Place copy in system clipboard",
                    copy_details_to_clipboard,
                    enabled=True,
                    hotkey="p",
                )
                # add_option("Schedule new instance", schedule_new_instance, enabled=True)
                # add_option(
                #     "Reschedule instance" if instance_ts else "Reschedule",
                #     reschedule_item,
                #     enabled=True,
                # )
                add_option(
                    "Open link with default", goto_item, enabled=has_links, hotkey="g"
                )
                add_option("Touch", touch_item, enabled=True, hotkey="t")
                add_option("Pin/Unpin", toggle_pin, enabled=itemtype == "~", hotkey="u")
                add_option(
                    "History of completions",
                    show_completions,
                    enabled=itemtype in "~^",
                    hotkey="h",
                )
                add_option(
                    "Show repetitions", show_repetitions, enabled=has_rrule, hotkey="r"
                )

                if not options:
                    app.notify(
                        "No actions available for this item.", severity="warning"
                    )
                    return

                subj = subject or "Untitled"
                color = "white"
                if itemtype:
                    color = TYPE_TO_COLOR.get(
                        itemtype, TYPE_TO_COLOR.get(itemtype.lower(), "white")
                    )
                message = f"[{color}]{subj}[/{color}]\nChoose an action:"

                def _after(choice: str | None) -> None:
                    if not choice:
                        return
                    cb = callbacks.get(choice)
                    if cb:
                        cb()

                app.push_screen(OptionPrompt(message, options), callback=_after)

            if key == "ENTER":
                show_action_menu()
                return

        return handler

    def on_key(self, event: events.Key) -> None:
        """Handle global key events (tags, escape, etc.)."""

        # --- View-specific setup ---
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
                        screen.previous_page()
                    else:
                        self.action_previous_week()
                    return

                else:  # right
                    if has_next_available and do_next:
                        screen.next_page()
                    else:
                        self.action_next_week()
                    return
            elif self.view == "year":
                if event.key == "left":
                    self.year_offset -= 1
                else:
                    self.year_offset += 1
                self.action_show_year()
                return
            # else: not week/year view -> let other code handle left/right
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
            return

        if self.leader_mode:
            self.leader_mode = False
            meta = self.controller.get_last_details_meta() or {}
            handler = getattr(self, "detail_handler", None)
            if handler:
                # 🔹 handler is now sync; just call it
                handler(f"comma,{event.key}", meta)
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
        self.notify(f"Screenshot saved to: {path}", severity="info", timeout=3)

    def _maybe_sync_inbox(self, now: datetime) -> None:
        if (
            now - getattr(self, "_last_inbox_check", datetime.min)
        ).total_seconds() < 900:
            return
        self._last_inbox_check = now
        try:
            added, errors = self.controller.sync_inbox()
        except Exception as exc:
            log_msg(f"Inbox sync failed: {exc}")
            self.notify(
                "Inbox sync failed — see log for details.",
                severity="warning",
                timeout=2.5,
            )
            return

        if added:
            plural = "s" if added != 1 else ""
            self.notify(
                f"Imported {added} draft{plural} from inbox.txt",
                severity="info",
                timeout=2.5,
            )
            try:
                self.refresh_view()
            except Exception:
                pass

        if errors:
            issue_plural = "s" if len(errors) != 1 else ""
            self.notify(
                f"Inbox sync had {len(errors)} issue{issue_plural}; see log.",
                severity="warning",
                timeout=3.0,
            )
            for err in errors:
                log_msg(f"Inbox sync warning: {err}")

    def run_daily_tasks(self, *, refresh: bool = True):
        created, kept, removed = self.controller.rotate_daily_backups()
        if created:
            log_msg(f"✅ Backup created: {created}")
        else:
            log_msg("ℹ️ No backup created (DB unchanged since last snapshot).")
        if removed:
            log_msg("🧹 Pruned: " + ", ".join(p.name for p in removed))

        self.today = date.today()
        self.controller.new_day()
        self.controller.populate_alerts()
        self.controller.populate_notice()
        # self._apply_update_indicator(check_update_available(VERSION))
        if not refresh:
            return

        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        if self.view == "weeks":
            self.update_table_and_list()
            return
        if self.view == "agenda":
            self.action_show_agenda()
            return

        self.refresh_view()

    def _daily_rollover_guard(self):
        """
        Timer callback that notices day changes even if alerts are idle.

        Previously this fired every minute and always called `run_daily_tasks`,
        which in turn kicked the UI back to Agenda because that action refreshes
        the Weeks/Agenda views. Guard it so we only refresh when the calendar
        day has actually advanced.
        """
        current = date.today()
        if getattr(self, "today", None) == current:
            return
        self.run_daily_tasks(refresh=True)

    def play_bells(self) -> None:
        """An action to ring the bell."""
        delay = [0.6, 0.4, 0.2]
        for d in delay:
            time.sleep(d)  # ~400 ms gap helps trigger distinct alerts
            self.app.bell()

    async def check_alerts(self):
        # called every 6 seconds
        now = datetime.now()
        self._maybe_sync_inbox(now)
        today = now.date()
        ## Run daily tasks at midnight
        if (
            now.hour == 0
            and now.minute == 0
            and 0 <= now.second < 6
            or self.today != today
        ):
            self.run_daily_tasks()
        ## Check for updates every 8 hours
        if now.hour % 8 == 0 and now.minute == 0 and 0 <= now.second < 6:
            bug_msg(
                f"checking for updates: {now.hour = }, {now.minute = }, {now.second = }"
            )
            self._apply_update_indicator(check_update_available(VERSION))

        ## Check alerts every 10 minutes
        if now.minute % 10 == 0 and now.second == 0:
            self.notify(
                "Checking for scheduled alerts...", severity="info", timeout=1.2
            )
        await self._maybe_run_current_command()
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

    async def _maybe_run_current_command(self) -> None:
        command = getattr(self.controller, "current_command", "").strip()
        if not command:
            return
        if self._current_command_task and not self._current_command_task.done():
            return ()
        payload = self.controller.consume_after_save_command()
        if not payload:
            return
        args, display = payload
        self._current_command_task = asyncio.create_task(
            self._run_current_command(args, display)
        )

    def _current_output_path(self) -> Path:
        home = getattr(self.controller.env, "home", None)
        if not home:
            home = Path.home() / ".config" / "tklr"
        else:
            home = Path(home)
        return home / "current.txt"

    def _write_current_output(self, data: bytes) -> None:
        path = self._current_output_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        text = data.decode("utf-8", errors="replace")
        path.write_text(text, encoding="utf-8")

    async def _run_current_command(self, args: list[str], display: str) -> None:
        env = os.environ.copy()
        if hasattr(self.controller, "env") and getattr(
            self.controller.env, "home", None
        ):
            env.setdefault("TKLR_HOME", str(self.controller.env.home))
        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, stderr = await proc.communicate()
            self._write_current_output(stdout or b"")
            if proc.returncode != 0:
                err = stderr.decode(errors="ignore").strip()
                log_msg(f"current_command failed ({proc.returncode}): {display}\n{err}")
                self.notify(
                    f"Current command failed ({proc.returncode})",
                    severity="warning",
                    timeout=4,
                )
        except Exception as exc:
            log_msg(f"current_command error for '{display}': {exc}")
            self.notify("Current command error", severity="warning", timeout=4)
        finally:
            self._current_command_task = None

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
        log_msg(f"{self.selected_week = }")
        title, table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        # self.set_afill("weeks")

        screen = WeeksScreen(title, table, details, footer)
        self.show_screen(screen)

    def action_show_year(self):
        self.view = "year"
        view_width = None
        if self.size.width:
            # Leave a little breathing room for panel padding and borders.
            view_width = max(40, int(self.size.width) - 4)
        lines, title = self.controller.get_year_calendar(
            self.year_offset, available_width=view_width
        )
        footer = (
            f"[bold {FOOTER}]left[/bold {FOOTER}] earlier  "
            f"[bold {FOOTER}]right[/bold {FOOTER}] later  "
            f"[bold {FOOTER}]space[/bold {FOOTER}] current  "
        )
        pages = [(lines, {})]
        screen = FullScreenList(pages, title, "", footer)
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

    def action_show_modified(self):
        self.view = "modified"
        details, title = self.controller.get_modified()
        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

    def action_show_goals(self):
        self.view = "goals"
        pages, title, header = self.controller.get_goals(include_future=True)
        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(pages, title, header, footer))

    def action_show_query(self):
        self.view = "query"
        self.show_screen(QueryScreen(controller=self.controller))

    def action_show_tags(self):
        self.view = "tags"
        details, title = self.controller.get_tag_view()
        log_msg(f"{details = }, {title = }")

        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

    def action_show_find(self):
        self.view = "find"
        search_input = Input(placeholder="Enter search term...", id="find_input")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_show_completions(self):
        self.view = "completions"
        details, title = self.controller.get_completions()

        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"
        self.show_screen(FullScreenList(details, title, "", footer))

    def action_show_alerts(self):
        self.view = "alerts"
        pages, header = self.controller.get_active_alerts()
        log_msg(f"{pages = }, {header = }")

        footer = f"[bold {FOOTER}]?[/bold {FOOTER}] Help  [bold {FOOTER}]/[/bold {FOOTER}] Search"

        self.push_screen(
            FullScreenList(pages, "Remaining Alerts for Today", header, footer)
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

    def _remember_week_context(self) -> None:
        if self.view == "weeks":
            self._week_state_before_editor = (
                self.current_start_date,
                self.selected_week,
            )
        else:
            self._week_state_before_editor = None

    def _after_edit(self, result: dict | None) -> None:
        week_snapshot = getattr(self, "_week_state_before_editor", None)
        self._week_state_before_editor = None

        if not result or not result.get("changed"):
            return

        if self.view == "weeks":
            if week_snapshot:
                saved_start, saved_week = week_snapshot
            else:
                saved_start, saved_week = self.current_start_date, self.selected_week

            self.current_start_date = saved_start
            self.selected_week = saved_week
            self.update_table_and_list()
        else:
            self.refresh_view()

    def open_editor_for(
        self, *, record_id: int | None = None, seed_text: str = ""
    ) -> None:
        self._remember_week_context()
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
            if search_term:
                try:
                    copy_to_clipboard(search_term)
                    self.notify(
                        "Search copied to clipboard ✓", severity="info", timeout=1.2
                    )
                except ClipboardUnavailable as exc:
                    self.notify(str(exc), severity="warning", timeout=2.5)
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
        if self.view == "year":
            self.year_offset = 0
            self.action_show_year()
            return
        self.current_start_date = calculate_4_week_start()
        self.selected_week = tuple(datetime.now().isocalendar()[:2])
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_next_period(self):
        if self.view == "year":
            self.year_offset += 1
            self.action_show_year()
            return
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        # self.set_afill("weeks")
        self.update_table_and_list()

    def action_previous_period(self):
        if self.view == "year":
            self.year_offset -= 1
            self.action_show_year()
            return
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

    def action_jump_to_week(self):
        """
        Prompt for a date and jump Weeks view to the week containing it.
        """

        def _after(result: str | None) -> None:
            if not result:
                return
            try:
                parsed = parse(result)
            except Exception as exc:
                self.notify(f"Could not parse '{result}': {exc}", severity="error")
                return
            if not parsed:
                self.notify("Enter a recognizable date (e.g. 2025-03-14).")
                return

            if isinstance(parsed, datetime):
                target_date = parsed.date()
            elif isinstance(parsed, date):
                target_date = parsed
            else:
                self.notify("Please enter a calendar date.", severity="warning")
                return

            iso_year, iso_week, _ = target_date.isocalendar()
            self.selected_week = (iso_year, iso_week)
            monday = datetime.strptime(f"{iso_year} {iso_week} 1", "%G %V %u")
            self.current_start_date = monday - timedelta(weeks=1)
            self.view = "weeks"
            self.update_table_and_list()

        if self.view != "weeks":
            self.action_show_weeks()

        self.push_screen(
            TextPrompt(
                "Jump to Date",
                message="Enter a date to view its week (e.g. 2025-03-14).",
                placeholder=" date...",
            ),
            callback=_after,
        )

    def action_quit(self):
        self.exit()

    def action_show_help(self):
        scr = self.screen
        if (
            hasattr(scr, "list_with_details")
            and scr.list_with_details.has_details_open()
        ):
            meta = self.controller.get_last_details_meta() or {}
            lines = build_details_help(meta)
            self.push_screen(HelpScreen(lines))
        elif self.view == "query":
            self.push_screen(HelpScreen(QueryHelpText))
        else:
            env = getattr(self.controller, "env", None)
            home_display = None
            if env is not None:
                home_path = getattr(env, "home", None)
                if home_path:
                    try:
                        home_display = collapse_home(home_path)
                    except Exception:
                        home_display = str(home_path)
            self.push_screen(HelpScreen(build_help_text(home_display)))

    def action_detail_edit(self):
        self._dispatch_detail_key("/e")

    def action_detail_copy(self):
        self._dispatch_detail_key("/c")

    def action_detail_delete(self):
        self._dispatch_detail_key("/d")

    def action_detail_finish(self):
        self._dispatch_detail_key("/f")

    def action_detail_goto(self):
        self._dispatch_detail_key("/g")

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

    # async def prompt_datetime(
    #     self, message: str, default: datetime | None = None
    # ) -> datetime | None:
    #     """Show DatetimePrompt and return parsed datetime or None."""
    #     return await self.push_screen_wait(DatetimePrompt(message, default))

    def prompt_datetime_with_callback(
        self,
        message: str,
        callback: Callable[[Optional[datetime]], None],
        default: datetime | None = None,
    ) -> None:
        """
        Show DatetimePrompt and call `callback(parsed_dt_or_None)` when done.
        No async/await required in the caller.
        """

        def _after(result: datetime | None) -> None:
            # `result` is whatever DatetimePrompt.dismiss(...) gave us
            callback(result)

        self.push_screen(
            DatetimePrompt(message=message, default=default),
            callback=_after,
        )

    async def prompt_options(self, message: str, options: list[str]) -> str | None:
        """Show OptionPrompt and return the chosen label, or None."""
        return await self.push_screen_wait(OptionPrompt(message, options))

    async def prompt_choice(self, message: str, choices: list[str]) -> str | None:
        """Show ChoicePrompt and return one of `choices` or None."""
        return await self.push_screen_wait(ChoicePrompt(message, choices))

    async def prompt_confirm(self, message: str) -> bool | None:
        """
        Show a Yes/No/Esc confirm dialog.

        Returns:
            True  -> Yes
            False -> No
            None  -> Esc/cancel
        """
        return await self.push_screen_wait(ConfirmPrompt(message))

    def action_show_bins(self, start_bin_id: int | None = None):
        root_id = start_bin_id or self.controller.get_root_bin_id()
        self.push_screen(TaggedHierarchyScreen(self.controller, root_id))

    def action_open_with_default(self, record_id: int) -> None:
        """
        Open the @g target for this record using the OS default handler.
        """
        # Get the record row + tokens JSON
        row = self.controller.db_manager.get_record_as_dictionary(record_id)
        if not row:
            self.notify(f"Record {record_id} not found.", severity="warning")
            return

        tokens_json = row.get("tokens")
        if not tokens_json:
            self.notify("This record has no tokens (no @g).", severity="warning")
            return

        try:
            tokens = json.loads(tokens_json) or []
        except Exception as e:
            self.notify(
                f"Cannot parse tokens for record {record_id}: {e}", severity="warning"
            )
            return
        tokens = reveal_mask_tokens(tokens, self.controller.mask_secret)

        goto_value: str | None = None

        for tok in tokens:
            if tok.get("t") != "@":
                continue
            if tok.get("k") != "g":
                continue

            # Prefer the parsed value if do_g stored it
            if "goto" in tok:
                goto_value = tok["goto"]
            else:
                raw = (tok.get("token") or "").strip()
                if raw.startswith("@g"):
                    goto_value = raw[2:].strip()
                else:
                    parts = raw.split(None, 1)
                    goto_value = parts[1].strip() if len(parts) > 1 else ""

            if goto_value:
                break

        if not goto_value:
            self.notify("This record has no @g link.", severity="warning")
            return

        # Finally, delegate to your OS opener
        try:
            bug_msg(f"Opening {goto_value = } with default application...")
            open_with_default(goto_value)
        except Exception as e:
            self.notify(f"Failed to open {goto_value!r}: {e}", severity="error")


if __name__ == "__main__":
    pass
