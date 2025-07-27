import tklr

from importlib.metadata import version
from .shared import log_msg, display_messages
from datetime import datetime, timedelta
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

tklr_version = version("tklr")
# from textual.errors import NoMatches

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
SELECTED_BACKGROUND = "#566573"
MATCH_COLOR = TOMATO
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
    # same_day = start_dt.day == end_dt.day
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
    # start_of_week = datetime.strptime(
    #     " ".join(map(str, [iso_year, iso_week, 1])), "%G %V %u"
    # )
    start_of_week = today - timedelta(days=iso_weekday - 1)
    weeks_into_cycle = (iso_week - 1) % 4
    return start_of_week - timedelta(weeks=weeks_into_cycle)


HelpText = f"""\
[bold][{TITLE_COLOR}]TKLR {VERSION}[/{TITLE_COLOR}][/bold]
[bold][{HEADER_COLOR}]Application Keys[/{HEADER_COLOR}][/bold]
  [bold]Q[/bold]:           Quit etm          [bold]S[/bold]:       Take Screenshot
[bold][{HEADER_COLOR}]View[/{HEADER_COLOR}][/bold]
  [bold]W[/bold]:           Weeks view        [bold]N[/bold]:       Next occurrences 
  [bold]F[/bold]:           Find in items     [bold]L[/bold]:       Last occurrences 
[bold][{HEADER_COLOR}]Search Keys[/{HEADER_COLOR}][/bold]
  [bold]/[/bold]:           Set search        Use an empty search to clear
  [bold]>[/bold]:           Next match        [bold]<[/bold]:       Previous match           
[bold][{HEADER_COLOR}]Navigation Keys[/{HEADER_COLOR}][/bold]
  [bold]left[/bold]:        previous week     [bold]up[/bold]:      up in the list
  [bold]right[/bold]:       next week         [bold]down[/bold]:    down in the list
  [bold]shift+left[/bold]:  previous 4-weeks  [bold]period[/bold]:  center week
  [bold]shift+right[/bold]: next 4-weeks      [bold]space[/bold]:   current 4-weeks 

[bold][{HEADER_COLOR}]Tags[/{HEADER_COLOR}][/bold] Each of the main views displays a list of items, with each item beginning with an alphabetic tag that can be used to display the details of the item. E.g., to see the details of the item tagged 'a', simply press 'a' on the keyboard. These tags are sequentially generated from 'a', 'b', ..., 'z', 'ba', 'bb', and so forth. Just press the corresponding key for each character in the tag. 
""".splitlines()


class DetailsScreen(Screen):
    """A temporary details screen."""

    # log_msg(f"DetailsScreen: {HelpText = }")

    def __init__(self, details: str):
        super().__init__()
        self.title = details[0]
        self.lines = details[1:]
        self.footer = [
            "",
            "[bold yellow]ESC[/bold yellow] return to previous screen",
        ]

    def compose(self) -> ComposeResult:
        yield Static(self.title, id="details_title", classes="title-class")
        yield Static("\n".join(self.lines), expand=True, id="details_text")
        yield Static("\n".join(self.footer), id="custom_footer")

    def on_key(self, event):
        if event.key == "escape":
            self.app.pop_screen()


class SearchableScreen(Screen):
    """Base class for screens that support search."""

    def perform_search(self, term: str):
        """Perform search within the screen if it has a ScrollableList with id 'list'."""
        try:
            scrollable_list = self.query_one("#list", ScrollableList)
            scrollable_list.set_search_term(term)
            scrollable_list.refresh()
        except NoMatches:
            log_msg(
                f"[SearchableScreen] No #list found in {self.id or self.__class__.__name__}"
            )
        except Exception as e:
            log_msg(f"[SearchableScreen] Error during search: {e}")

    def clear_search(self):
        """Clear search highlights from the ScrollableList if it exists."""
        try:
            scrollable_list = self.query_one("#list", ScrollableList)
            scrollable_list.clear_search()
            scrollable_list.refresh()
        except NoMatches:
            log_msg(f"[SearchableScreen] No #list found to clear.")
        except Exception as e:
            log_msg(f"[SearchableScreen] Error clearing search: {e}")

    def scroll_to_next_match(self):
        scrollable_list = self.query_one("#list", ScrollableList)
        current_y = scrollable_list.scroll_offset.y
        next_match = next((i for i in scrollable_list.matches if i > current_y), None)
        if next_match is not None:
            scrollable_list.scroll_to(0, next_match)
            scrollable_list.refresh()

    def scroll_to_previous_match(self):
        scrollable_list = self.query_one("#list", ScrollableList)
        current_y = scrollable_list.scroll_offset.y
        prev_match = next(
            (i for i in reversed(scrollable_list.matches) if i < current_y), None
        )
        if prev_match is not None:
            scrollable_list.scroll_to(0, prev_match)
            scrollable_list.refresh()


MATCH_COLOR = "yellow"


class ScrollableList(ScrollView):
    """A scrollable list widget with a fixed title and search functionality."""

    def __init__(self, lines: list[str], **kwargs) -> None:
        super().__init__(**kwargs)
        width = shutil.get_terminal_size().columns - 3
        self.lines = [Text.from_markup(line) for line in lines]
        self.virtual_size = Size(width, len(self.lines))
        self.console = Console()
        self.search_term = None
        self.matches = []

    def set_search_term(self, search_term: str):
        self.clear_search()
        self.search_term = search_term.lower() if search_term else None
        self.matches = [
            i
            for i, line in enumerate(self.lines)
            if self.search_term and self.search_term in line.plain.lower()
        ]
        if self.matches:
            self.scroll_to(0, self.matches[0])
            self.refresh()

    def clear_search(self):
        self.search_term = None
        self.matches = []
        self.refresh()

    def render_line(self, y: int) -> Strip:
        scroll_x, scroll_y = self.scroll_offset
        y += scroll_y
        if y < 0 or y >= len(self.lines):
            return Strip.blank(self.size.width)
        line_text = self.lines[y].copy()
        if self.search_term and y in self.matches:
            line_text.stylize(f"bold {MATCH_COLOR}")
        segments = list(line_text.render(self.console))
        cropped_segments = Segment.adjust_line_length(
            segments, self.size.width, style=None
        )
        return Strip(cropped_segments, self.size.width)

    def update_list(self, new_lines: list[str]) -> None:
        self.lines = [Text.from_markup(line) for line in new_lines]
        self.virtual_size = Size(
            shutil.get_terminal_size().columns - 3, len(self.lines)
        )
        self.refresh()


class WeeksScreen(SearchableScreen):  # instead of Screen
    def __init__(
        self,
        title: str,
        table: str,
        list_title: str,
        details: list[str],
        footer_content: str = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search",
    ):
        super().__init__()
        self.table_title = title
        self.table = table
        self.list_title = list_title
        self.details = details
        self.footer_content = footer_content

    async def on_mount(self) -> None:
        self.update_table_and_list()

    def compose(self) -> ComposeResult:
        yield Static(
            self.table_title or "Untitled", id="table_title", classes="title-class"
        )
        yield Static(self.table or "[i]No data[/i]", id="table", classes="weeks-table")
        yield Static(self.list_title, id="list_title", classes="title-class")
        yield ScrollableList(self.details, id="list")
        yield Static(self.footer_content, id="custom_footer")

    def update_table_and_list(self):
        title, table, details = self.app.controller.get_table_and_list(
            self.app.current_start_date, self.app.selected_week
        )
        self.query_one("#table_title", expect_type=Static).update(title)
        self.query_one("#table", expect_type=Static).update(table)
        self.query_one("#list_title", expect_type=Static).update(details[0])
        self.query_one("#list", expect_type=ScrollableList).update_list(details[1:])


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
        self.footer_content = footer_content
        log_msg(f"FullScreenList: {details[:3] = }")

    def compose(self) -> ComposeResult:
        """Compose the layout."""
        # yield Static(self.title, id="scroll_title", classes="title-class")
        # yield ScrollableList(self.lines, id="list")  # Using "list" as the ID
        # yield Static(self.footer_content, id="custom_footer")

        yield Static(self.title, id="scroll_title", expand=True, classes="title-class")
        yield Static(
            self.header, id="scroll_header", expand=True, classes="header-class"
        )
        yield Static(
            Rule("", style="#fff8dc"), id="separator"
        )  # Add a horizontal line separator
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
        ("S", "take_screenshot", "Take Screenshot"),
        ("A", "show_alerts", "Show Alerts"),
        ("L", "show_last", "Show Last"),
        ("N", "show_next", "Show Next"),
        ("F", "show_find", "Find"),
        ("W", "show_weeks", "Show Weeks"),
        ("?", "show_help", "Help"),
        ("Q", "quit", "Quit"),
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

    def set_afill(self, details: list, method: str):
        if self.view == "week":
            log_msg(f"{self.selected_week = }")
            week = self.controller.tag_to_id.get(self.selected_week, None)
            if week:
                tag_to_id = week
            else:
                log_msg(f"invalid week: {self.selected_week = }")
                return ["Invalid week"]

            # tag_to_id = self.controller.tag_to_id.get(self.selected_week, None)
        elif self.view in ["next", "last", "find"]:
            tag_to_id = self.controller.list_tag_to_id[self.view]
        elif self.view == "alerts":
            tag_to_id = self.controller.list_tag_to_id["alerts"]
        else:
            return ["Invalid view."]
        num_tags = len(tag_to_id.keys())
        new_afill = 1 if num_tags <= 26 else 2 if num_tags <= 676 else 3
        if new_afill != self.afill:
            old_afill = self.afill
            self.afill = new_afill
            log_msg(f"view reset afill in {method} from {old_afill} -> {self.afill}")

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
        now = datetime.now()
        if now.hour == 0 and now.minute == 0 and 0 <= now.second < 6:
            self.controller.populate_alerts()
        if now.minute % 10 == 0 and now.second == 0:
            self.notify("Checking for due alerts...", severity="info")
        self.controller.execute_due_alerts()

    def action_show_weeks(self):
        self.view = "week"
        title, table, details = self.controller.get_table_and_list(
            self.current_start_date, self.selected_week
        )
        list_title = details[0] if details else "Untitled"
        details = details[1:] if details else []
        log_msg(f"{len(details) = }")
        self.set_afill(details, "action_show_weeks")
        footer = "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] Search"
        self.push_screen(WeeksScreen(title, table, list_title, details, footer))

    def action_show_last(self):
        self.view = "last"
        details = self.controller.get_last()
        self.set_afill(details, "action_show_last")
        footer = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] ESC Back"
        )
        self.push_screen(FullScreenList(details, footer))

    def action_show_next(self):
        self.view = "next"
        details = self.controller.get_next()
        self.set_afill(details, "action_show_next")

        footer = (
            "[bold yellow]?[/bold yellow] Help [bold yellow]/[/bold yellow] ESC Back"
        )
        self.push_screen(FullScreenList(details, footer))

    def action_show_find(self):
        self.view = "find"
        search_input = Input(placeholder="Enter search term...", id="find_input")
        self.mount(search_input)
        self.set_focus(search_input)

    def action_show_alerts(self):
        self.view = "alerts"
        details = self.controller.get_active_alerts()
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
        self.update_table_and_list()

    def action_next_period(self):
        self.current_start_date += timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.update_table_and_list()

    def action_previous_period(self):
        self.current_start_date -= timedelta(weeks=4)
        self.selected_week = tuple(self.current_start_date.isocalendar()[:2])
        self.update_table_and_list()

    def action_next_week(self):
        self.selected_week = get_next_yrwk(*self.selected_week)
        if self.selected_week > tuple(
            (self.current_start_date + timedelta(weeks=4) - ONEDAY).isocalendar()[:2]
        ):
            self.current_start_date += timedelta(weeks=1)
        self.update_table_and_list()

    def action_previous_week(self):
        self.selected_week = get_previous_yrwk(*self.selected_week)
        if self.selected_week < tuple((self.current_start_date).isocalendar()[:2]):
            self.current_start_date -= timedelta(weeks=1)
        self.update_table_and_list()

    def action_center_week(self):
        self.current_start_date = datetime.strptime(
            f"{self.selected_week[0]} {self.selected_week[1]} 1", "%G %V %u"
        ) - timedelta(weeks=1)
        self.update_table_and_list()

    def action_quit(self):
        self.exit()

    def action_show_help(self):
        self.push_screen(DetailsScreen(HelpText))

    def action_show_details(self, tag: str):
        details = self.controller.process_tag(tag, self.view, self.selected_week)
        self.push_screen(DetailsScreen(details))


if __name__ == "__main__":
    pass
