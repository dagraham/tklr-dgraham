# TODO: Keep the display part - the model part will be in model.py
from datetime import datetime, timedelta
from logging import log
from sre_compile import dis
from prompt_toolkit.styles.named_colors import NAMED_COLORS
from rich.console import Console
from rich.table import Table
from rich.box import HEAVY_EDGE
from rich import style
from rich.columns import Columns
from rich.console import Group, group
from rich.panel import Panel
from rich.layout import Layout
from rich import print as rprint
import re
import inspect
from rich.theme import Theme
from rich import box
from typing import List, Tuple, Dict
from bisect import bisect_left, bisect_right

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.shortcuts import PromptSession
import string
import shutil
import subprocess
import shlex
from typing import Literal

from .model import DatabaseManager

from .common import truncate_string, format_extent
from .shared import (
    log_msg,
    HRS_MINS,
    ALERT_COMMANDS,
    format_time_range,
    format_timedelta,
    format_datetime,
    truncate_string,
)

# The overall background color of the app is #2e2e2e - set in view_textual.css
DAY_COLOR = NAMED_COLORS["LemonChiffon"]
FRAME_COLOR = NAMED_COLORS["Grey"]
DIM_COLOR = NAMED_COLORS["DarkGray"]
# EVENT_COLOR = NAMED_COLORS["LimeGreen"]
EVENT_COLOR = NAMED_COLORS["LightGreen"]
AVAILABLE_COLOR = NAMED_COLORS["LightSkyBlue"]
WAITING_COLOR = NAMED_COLORS["SlateGrey"]
FINISHED_COLOR = NAMED_COLORS["DarkGrey"]
GOAL_COLOR = NAMED_COLORS["GoldenRod"]
CHORE_COLOR = NAMED_COLORS["Khaki"]
PASTDUE_COLOR = NAMED_COLORS["DarkOrange"]
BEGIN_COLOR = NAMED_COLORS["Gold"]
INBOX_COLOR = NAMED_COLORS["OrangeRed"]
TODAY_COLOR = NAMED_COLORS["Tomato"]
SELECTED_BACKGROUND = "#4e4e4e"
# SELECTED_BACKGROUND = "#3b3b3b"
# SELECTED_BACKGROUND = "#3d3d3d"
# SELECTED_BACKGROUND = "#4d4d4d"
# SELECTED_BACKGROUND = "#5d5d5d"
# SELECTED_BACKGROUND = "#737373"

BUSY_COLOR = NAMED_COLORS["YellowGreen"]
CONF_COLOR = NAMED_COLORS["Tomato"]
# BUSY_FRAME_COLOR = "#4e4e4e"
BUSY_FRAME_COLOR = "#5d5d5d"
# BUSY_FRAME_COLOR = "#6e6e6e"
# BUSY_FRAME_COLOR = NAMED_COLORS["DimGrey"]
# SLOT_HOURS = [0, 4, 8, 12, 16, 20, 24]
SLOT_HOURS = [0, 6, 12, 18, 24]
SLOT_MINUTES = [x * 60 for x in SLOT_HOURS]
BUSY = "■"  # U+25A0 this will be busy_bar busy and conflict character
FREE = "□"  # U+25A1 this will be busy_bar free character
ADAY = "━"  # U+2501 for all day events ━

SELECTED_COLOR = NAMED_COLORS["Yellow"]
# SELECTED_COLOR = "bold yellow"

HEADER_COLOR = NAMED_COLORS["LemonChiffon"]
HEADER_STYLE = f"bold {NAMED_COLORS['LemonChiffon']}"
FIELD_COLOR = NAMED_COLORS["SkyBlue"]

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
    "!": INBOX_COLOR,  # inbox
}


def format_hours_mins(dt: datetime, mode: Literal["24", "12"]) -> str:
    """
    Format a datetime object as hours and minutes.
    """
    fmt = {
        "24": "%H:%M",
        "12": "%I:%M%p",
    }
    if mode == "12":
        return dt.strftime(fmt[mode]).lower().rstrip("m")
    return f"{dt.strftime(fmt[mode])}"


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


# def base26_to_decimal(base26_num):
#     """
#     Convert an arbitrary-length base-26 number to its decimal equivalent.
#
#     Args:
#         base26_num (str): A base-26 string using 'a' as 0 and 'z' as 25.
#
#     Returns:
#         int: The decimal equivalent of the base-26 number.
#     """
#     decimal_value = 0
#     length = len(base26_num)
#
#     # Process each character in the base-26 string
#     for i, char in enumerate(base26_num):
#         digit = ord(char) - ord("a")  # Map 'a' to 0, ..., 'z' to 25
#         power = length - i - 1  # Compute the power of 26
#         decimal_value += digit * (26**power)
#
#     return decimal_value


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


def base26_to_decimal(base26_num):
    """
    Convert a 2-digit base-26 number to its decimal equivalent.

    Args:
        base26_num (str): A 2-character string in base-26 using 'a' as 0 and 'z' as 25.

    Returns:
        int: The decimal equivalent of the base-26 number.
    """
    # Ensure the input is exactly 2 characters
    if len(base26_num) != 2:
        raise ValueError("Input must be a 2-character base-26 number.")

    # Map each character to its base-26 value
    digit1 = ord(base26_num[0]) - ord("a")  # First character
    digit2 = ord(base26_num[1]) - ord("a")  # Second character

    # Compute the decimal value
    decimal_value = digit1 * 26**1 + digit2 * 26**0

    return decimal_value


def indx_to_tag(indx: int, fill: int = 1):
    """
    Convert an index to a base-26 tag.
    """
    return decimal_to_base26(indx).rjust(fill, "a")


def event_tuple_to_minutes(start_dt: datetime, end_dt: datetime) -> Tuple[int, int]:
    """
    Convert event start and end datetimes to minutes since midnight.

    Args:
        start_dt (datetime): Event start datetime.
        end_dt (datetime): Event end datetime.

    Returns:
        Tuple(int, int): Tuple of start and end minutes since midnight.
    """
    start_minutes = start_dt.hour * 60 + start_dt.minute
    end_minutes = end_dt.hour * 60 + end_dt.minute
    return (start_minutes, end_minutes)


def get_busy_bar(events):
    """
    Determine slot states (0: free, 1: busy, 2: conflict) for a list of events.

    Args:
        L (List[int]): Sorted list of slot boundaries.
        events (List[Tuple[int, int]]): List of event tuples (start, end).

    Returns:
        List[int]: A list where 0 indicates a free slot, 1 indicates a busy slot,
                and 2 indicates a conflicting slot.
    """
    # Initialize slot usage as empty lists
    L = SLOT_MINUTES
    slot_events = [[] for _ in range(len(L) - 1)]
    allday = 0

    for b, e in events:
        # Find the start and end slots for the current event

        if b == 0 and e == 0:
            allday += 1
        if e == b and not allday:
            continue

        start_slot = bisect_left(L, b) - 1
        end_slot = bisect_left(L, e) - 1

        # Track the event in each affected slot
        for i in range(start_slot, min(len(slot_events), end_slot + 1)):
            if L[i + 1] > b and L[i] < e:  # Ensure overlap with the slot
                slot_events[i].append((b, e))

    # Determine the state of each slot
    slots_state = []
    for i, events_in_slot in enumerate(slot_events):
        if not events_in_slot:
            # No events in the slot
            slots_state.append(0)
        elif len(events_in_slot) == 1:
            # Only one event in the slot, so it's busy but not conflicting
            slots_state.append(1)
        else:
            # Check for overlaps to determine if there's a conflict
            events_in_slot.sort()  # Sort events by start time
            conflict = False
            for j in range(len(events_in_slot) - 1):
                _, end1 = events_in_slot[j]
                start2, _ = events_in_slot[j + 1]
                if start2 < end1:  # Overlap detected
                    conflict = True
                    break
            slots_state.append(2 if conflict else 1)

    busy_bar = ["_" for _ in range(len(slots_state))]
    have_busy = False
    for i in range(len(slots_state)):
        if slots_state[i] == 0:
            busy_bar[i] = f"[dim]{FREE}[/dim]"
        elif slots_state[i] == 1:
            have_busy = True
            busy_bar[i] = f"[{BUSY_COLOR}]{BUSY}[/{BUSY_COLOR}]"
        else:
            have_busy = True
            busy_bar[i] = f"[{CONF_COLOR}]{BUSY}[/{CONF_COLOR}]"

    # return slots_state, "".join(busy_bar)
    busy_str = (
        f"\n[{BUSY_FRAME_COLOR}]{''.join(busy_bar)}[/{BUSY_FRAME_COLOR}]"
        if have_busy
        else "\n"
    )

    aday_str = f"[{BUSY_COLOR}]{ADAY}[/{BUSY_COLOR}]" if allday > 0 else ""

    return aday_str, busy_str


class Controller:
    def __init__(self, database_path: str):
        # Initialize the database manager
        self.db_manager = DatabaseManager(database_path)
        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.yrwk_to_details = {}  # Maps (iso_year, iso_week), to the details for that week
        self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week) for the current period
        self.start_date = calculate_4_week_start()
        self.selected_week = tuple(
            datetime.now().isocalendar()[:2]
        )  # Currently selected week
        self.tag_to_id = {}  # Maps tag numbers to event IDs
        self.list_tag_to_id = {}  # Maps tag numbers to event IDs

    def get_record_details_as_string(self, record_id):
        """
        Retrieve and format the details of a record as a string.

        Args:
            record_id (int): The ID of the record to retrieve.

        Returns:
            str: A formatted string with the record's details.
        """
        # log_msg(f"Fetching details for record ID {record_id}")
        self.db_manager.cursor.execute(
            """
            SELECT id, type, name, details, rrulestr, extent
            FROM Records
            WHERE id = ?
            """,
            (record_id,),
        )
        record = self.db_manager.cursor.fetchone()
        # log_msg(f"Record: {record = }")

        if not record:
            return f"[red]No record found for ID {record_id}[/red]"

        fields = ["Id", "Type", "Name e", "Details", "RRule", "Extent"]
        content = "\n".join(
            f" [cyan]{field}:[/cyan] [white]{value if value is not None else '[dim]NULL[/dim]'}[/white]"
            for field, value in zip(fields, record)
        )
        # log_msg(f"Content: {content}")
        return content

    def populate_alerts(self):
        self.db_manager.populate_alerts()

    def execute_alert(self, command: str):
        """
        Execute the given alert command using subprocess.

        Args:
            command (str): The command string to execute.
        """
        if not command:
            print("❌ Error: No command provided to execute.")
            return

        try:
            # ✅ Use shlex.split() to safely parse the command
            subprocess.run(shlex.split(command), check=True)
            print(f"✅ Successfully executed: {command}")
        except subprocess.CalledProcessError as e:
            print(f"❌ Error executing command: {command}\n{e}")
        except FileNotFoundError:
            print(f"❌ Command not found: {command}")
        except Exception as e:
            print(f"❌ Unexpected error: {e}")

    def execute_due_alerts(self):
        records = self.db_manager.get_due_alerts()
        # SELECT alert_id, record_id, record_name, trigger_datetime, start_timedelta, command
        for record in records:
            (
                alert_id,
                record_id,
                record_name,
                trigger_datetime,
                start_datetime,
                alert_command,
            ) = record
            log_msg(f"Executing alert {alert_command = }, {trigger_datetime = }")
            self.execute_alert(alert_command)
            # need command to execute command with arguments
            self.db_manager.mark_alert_executed(alert_id)

    def get_active_alerts(self, width: int = 70):
        # now_fmt = datetime.now().strftime("%A, %B %-d %H:%M:%S")
        alerts = self.db_manager.get_active_alerts()
        header = "Remaining alerts for today"
        results = [header]
        if not alerts:
            results.append(f" [{HEADER_COLOR}]none scheduled[/{HEADER_COLOR}]")
            return results

        table = Table(title="Remaining alerts for today", expand=True, box=HEAVY_EDGE)
        table.add_column("row", justify="center", width=3, style="dim")
        table.add_column("cmd", justify="center", width=3)
        table.add_column("time", justify="left", width=24)
        table.add_column("name", width=25, overflow="ellipsis", no_wrap=True)

        # 4*2 + 2*3 + 7 + 14 = 35 => name width = width - 35
        name_width = width - 35
        results.append(
            # f"{'row':^3}  {'cmd':^3}  {'time':^24}  {'name':^{name_width}}",
            f"[bold]{'row':^3}  {'cmd':^3}  {'alert':^7}  {'event time':^14}  {'name':^{name_width}}[/bold]",
        )

        self.list_tag_to_id.setdefault("alerts", {})
        self.afill = 1 if len(alerts) <= 26 else 2 if len(alerts) <= 676 else 3
        indx = 0
        tag = indx_to_tag(indx, self.afill)
        for alert in alerts:
            log_msg(f"Alert: {alert = }")
            # alert_id, record_id, record_name, start_dt, td, command
            (
                alert_id,
                record_id,
                record_name,
                trigger_datetime,
                start_datetime,
                alert_name,
                alert_command,
            ) = alert
            tag = indx_to_tag(indx, self.afill)
            self.list_tag_to_id["alerts"][tag] = record_id
            indx += 1
            trtime = format_datetime(trigger_datetime)
            tdtime = format_timedelta(start_datetime - trigger_datetime)
            sttime = format_datetime(start_datetime)
            # starting = f"{format_datetime(trigger_datetime):<7} {format_timedelta(start_datetime - trigger_datetime):>4} → {format_datetime(start_datetime)}"
            name = truncate_string(record_name, name_width)
            row = "  ".join(
                [
                    f"[dim]{tag:^3}[/dim]",
                    f"[bold yellow]{alert_name:^3}[/bold yellow]",
                    f"[bold yellow]{trtime:<7}[/bold yellow]",
                    f"[{EVENT_COLOR}]{tdtime:>4} → {sttime:<7}[/{EVENT_COLOR}]",
                    f"[{AVAILABLE_COLOR}]{name:<{name_width}}[/{AVAILABLE_COLOR}]",
                ]
            )
            results.append(row)
        return results

    def get_record_details(self, record_id):
        """
        Retrieve and format the details of a record as a list.

        Args:
            record_id (int): The ID of the record to retrieve.

        Returns:
            str: A formatted string with the record's details.
        """
        # log_msg(f"Fetching details for record ID {record_id}")
        self.db_manager.cursor.execute(
            """
            SELECT id, type, name, details, rrulestr, extent
            FROM Records
            WHERE id = ?
            """,
            (record_id,),
        )
        record = self.db_manager.cursor.fetchone()
        # log_msg(f"Record: {record = }")

        if not record:
            return [
                f"[red]No record found for ID {record_id}[/red]",
            ]

        fields = ["Id", "Type", "Name", "Details", "RRule", "Extent"]
        width = max(len(field) for field in fields) + 1
        content = [
            f"[{FIELD_COLOR}]{field:<{width}}[/{FIELD_COLOR}] [white]{value if value is not None else '[dim]NULL[/dim]'}[/white]"
            for field, value in zip(fields, record)
        ]
        # log_msg(f"Content: {content}")
        return content

    def process_tag(self, tag, view: str, selected_week: Tuple[int, int]):
        """
        Process the base26 tag entered by the user.

        Args:
            tag (str): The tag corresponding to a record.
        """
        if view == "week":
            log_msg(f"{self.selected_week = }")
            tag_to_id = self.tag_to_id[selected_week]
        elif view in ["next", "last", "find"]:
            tag_to_id = self.list_tag_to_id[view]
        elif view == "alerts":
            tag_to_id = self.list_tag_to_id["alerts"]
        else:
            return [
                "Invalid view.",
            ]

        # details = [f"Tag [{SELECTED_COLOR}]{tag}[/{SELECTED_COLOR}] details"]
        if tag in tag_to_id:
            record_id = tag_to_id[tag]
            details = [f"Details for [{SELECTED_COLOR}]{record_id}[/{SELECTED_COLOR}]"]
            # log_msg(f"Tag '{tag}' corresponds to record ID {record_id}")
            # details = self.get_record_details_as_string(record_id)
            fields = self.get_record_details(record_id)
            return details + fields

        return [f"There is no item corresponding to tag '{tag}'."]

    def generate_table(self, start_date, selected_week, grouped_events):
        """
        Generate a Rich table displaying events for the specified 4-week period.
        """
        # self.selected_week = selected_week
        selected_week = self.selected_week
        end_date = start_date + timedelta(weeks=4) - ONEDAY  # End on a Sunday
        start_date = start_date
        today_year, today_week, today_weekday = datetime.now().isocalendar()
        tomorrow_year, tomorrow_week, tomorrow_day = (
            datetime.now() + ONEDAY
        ).isocalendar()
        title = format_date_range(start_date, end_date)

        table = Table(
            show_header=True,
            header_style=HEADER_STYLE,
            show_lines=True,
            style=FRAME_COLOR,
            expand=True,
            box=box.SQUARE,
            # title=title,
            # title_style="bold",
        )

        weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        # table.add_column(f"[{DIM_COLOR}]Wk[/{DIM_COLOR}]", justify="center", width=3)
        for day in weekdays:
            table.add_column(
                day,
                justify="center",
                style=DAY_COLOR,
                width=8,
                ratio=1,
            )

        self.rownum_to_details = {}  # Reset for this period
        current_date = start_date
        weeks = []
        row_num = 0
        while current_date <= end_date:
            yr_wk = current_date.isocalendar()[:2]
            iso_year, iso_week = yr_wk
            if yr_wk not in weeks:
                weeks.append(yr_wk)
            # row_num += 1
            row_num = f"{yr_wk[1]:>2}"
            self.rownum_to_yrwk[row_num] = yr_wk
            # row = [f"[{DIM_COLOR}]{row_num}[{DIM_COLOR}]\n"]
            SELECTED = yr_wk == selected_week
            # row = (
            #     [f"[{SELECTED_COLOR}]{row_num}[/{SELECTED_COLOR}]\n"]
            #     if SELECTED
            #     else [f"[{DIM_COLOR}]{row_num}[{DIM_COLOR}]\n"]
            # )
            # row = [f"[{DIM_COLOR}]{row_num}[{DIM_COLOR}]\n"]
            row = []

            for weekday in range(1, 8):  # ISO weekdays: 1 = Monday, 7 = Sunday
                date = datetime.strptime(f"{iso_year} {iso_week} {weekday}", "%G %V %u")
                monthday_str = date.strftime(
                    "%-d"
                )  # Month day as string without leading zero
                events = (
                    grouped_events.get(iso_year, {}).get(iso_week, {}).get(weekday, [])
                )
                today = (
                    iso_year == today_year
                    and iso_week == today_week
                    and weekday == today_weekday
                )
                tomorrow = (
                    iso_year == tomorrow_year
                    and iso_week == tomorrow_week
                    and weekday == tomorrow_day
                )

                # mday = monthday_str
                mday = f"{monthday_str:>2}"
                if today:
                    mday = (
                        f"[bold][{TODAY_COLOR}]{monthday_str:>2}[/{TODAY_COLOR}][/bold]"
                    )

                if events:
                    tups = [event_tuple_to_minutes(ev[0], ev[1]) for ev in events]
                    aday_str, busy_str = get_busy_bar(tups)
                    # log_msg(f"{date = }, {tups = }, {busy_str = }")
                    if aday_str:
                        row.append(f"{aday_str + mday + aday_str:>4}{busy_str}")
                    else:
                        row.append(f"{mday:>2}{busy_str}")
                else:
                    row.append(f"{mday}\n")

                if SELECTED:
                    # row = [
                    #     f"[{SELECTED_COLOR}]{cell}[/{SELECTED_COLOR}]" for cell in row
                    # ]
                    # row = [
                    #     f"[{DIM_COLOR}]{row[0]}[{DIM_COLOR}]",
                    # ] + [
                    #     f"[{SELECTED_COLOR}]{cell}[/{SELECTED_COLOR}]"
                    #     for cell in row[1:]
                    # ]
                    row = [
                        f"[{SELECTED_COLOR}]{cell}[/{SELECTED_COLOR}]" for cell in row
                    ]
            if SELECTED:
                # table.add_row(*row)
                table.add_row(*row, style=f"on {SELECTED_BACKGROUND}")
                # table.add_row(Panel.fit(row))

            else:
                table.add_row(*row)
            self.yrwk_to_details[yr_wk] = self.get_week_details((iso_year, iso_week))
            current_date += timedelta(weeks=1)

        return title, table

    def get_table_and_list(self, start_date: datetime, selected_week: Tuple[int, int]):
        """
        - rich_display(start_datetime, selected_week)
            - sets:
                self.tag_to_id = {}  # Maps tag numbers to event IDs
                self.yrwk_to_details = {}  # Maps (iso_year, iso_week), to the details for that week
                self.rownum_to_yrwk = {}  # Maps row numbers to (iso_year, iso_week) for the current period
            - return title
            - return table
            - return details for selected_week
        """
        # today_year, today_week, today_weekday = datetime.now().isocalendar()
        # tomorrow_year, tomorrow_week, tomorrow_day = (
        #     datetime.now() + ONEDAY
        # ).isocalendar()
        log_msg(f"Getting table for {start_date = }, {selected_week = }")
        self.selected_week = selected_week
        current_start_year, current_start_week, _ = start_date.isocalendar()
        self.db_manager.extend_datetimes_for_weeks(
            current_start_year, current_start_week, 4
        )
        grouped_events = self.db_manager.process_events(
            start_date, start_date + timedelta(weeks=4)
        )

        # terminal_width = shutil.get_terminal_size().columns
        # Generate the table
        title, table = self.generate_table(start_date, selected_week, grouped_events)
        log_msg(f"Generated table for {title}, {selected_week = }")

        if selected_week in self.yrwk_to_details:
            details = self.yrwk_to_details[selected_week]
        else:
            details = "No week selected."
        return title, table, details

    def get_week_details(self, yr_wk):
        """
        Fetch and format details for a specific week.
        """
        log_msg(f"Getting details for week {yr_wk}")
        today_year, today_week, today_weekday = datetime.now().isocalendar()
        tomorrow_year, tomorrow_week, tomorrow_day = (
            datetime.now() + ONEDAY
        ).isocalendar()

        self.selected_week = yr_wk
        start_datetime = datetime.strptime(f"{yr_wk[0]} {yr_wk[1]} 1", "%G %V %u")
        end_datetime = start_datetime + timedelta(weeks=1)
        events = self.db_manager.get_events_for_period(start_datetime, end_datetime)
        # log_msg(f"from get_events_for_period:\n{events = }")
        this_week = format_date_range(start_datetime, end_datetime - ONEDAY)
        terminal_width = shutil.get_terminal_size().columns

        # header = f"Items for {this_week} #{yr_wk[1]} ({len(events)})"
        header = f"{this_week} #{yr_wk[1]} ({len(events)})"
        # details = [f"[not bold][{HEADER_COLOR}]{header}[/{HEADER_COLOR}][/not bold]"]
        details = [header]

        if not events:
            details.append(
                f" [{HEADER_COLOR}]Nothing scheduled for this week[/{HEADER_COLOR}]"
            )
            # return "\n".join(details)
            return details

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.afill = 1 if len(events) <= 26 else 2 if len(events) <= 676 else 3

        self.tag_to_id.setdefault(yr_wk, {})
        weekday_to_events = {}
        for i in range(7):
            this_day = (start_datetime + timedelta(days=i)).date()
            weekday_to_events[this_day] = []

        for start_ts, end_ts, type, name, id in events:
            start_dt = datetime.fromtimestamp(start_ts)
            end_dt = datetime.fromtimestamp(end_ts)
            # log_msg(f"Week details {name = }, {start_dt = }, {end_dt = }")

            if start_dt == end_dt:
                if start_dt.hour == 0 and start_dt.minute == 0 and start_dt.second == 0:
                    # start_end = f"{str('~'):^11}"
                    start_end = ""
                elif (
                    start_dt.hour == 23
                    and start_dt.minute == 59
                    and start_dt.second == 59
                ):
                    # start_end = f"{str('~'):^11}"
                    start_end = ""
                else:
                    start_end = f"{format_time_range(start_dt, end_dt, HRS_MINS)}"
            else:
                start_end = f"{format_time_range(start_dt, end_dt, HRS_MINS)}"

            type_color = TYPE_TO_COLOR[type]
            escaped_start_end = (
                f"[not bold]{start_end} [/not bold]" if start_end else ""
            )

            row = [
                id,
                f"[{type_color}]{type} {escaped_start_end}{name}[/{type_color}]",
            ]
            weekday_to_events.setdefault(start_dt.date(), []).append(row)

        indx = 0

        tag = indx_to_tag(indx, self.afill)

        for day, events in weekday_to_events.items():
            # TODO: today, tomorrow here
            iso_year, iso_week, weekday = day.isocalendar()
            today = (
                iso_year == today_year
                and iso_week == today_week
                and weekday == today_weekday
            )
            tomorrow = (
                iso_year == tomorrow_year
                and iso_week == tomorrow_week
                and weekday == tomorrow_day
            )
            flag = " (today)" if today else " (tomorrow)" if tomorrow else ""
            if events:
                details.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    # f"[not bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/not bold]"
                    f"[bold][{HEADER_COLOR}]{day.strftime('%a, %b %-d')}{flag}[/{HEADER_COLOR}][/bold]"
                )
                for event in events:
                    event_id, event_str = event
                    # log_msg(f"{event_str = }")
                    tag = indx_to_tag(indx, self.afill)
                    self.tag_to_id[yr_wk][tag] = event_id
                    details.append(f" [dim]{tag}[/dim]   {event_str}")
                    indx += 1
        # NOTE: maybe return list for scrollable view?
        # details_str = "\n".join(details)
        self.yrwk_to_details[yr_wk] = details
        return details

    def get_next(self):
        """
        Fetch and format details for the next instances.
        """
        events = self.db_manager.get_next_instances()
        header = f"next instances ({len(events)})"
        # details = [f"[not bold][{header_color}]{header}[/{header_color}][/not bold]"]
        details = [header]

        if not events:
            details.append(f" [{header_color}]nothing found[/{header_color}]")
            # return "\n".join(details)
            return details

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.afill = 1 if len(events) <= 26 else 2 if len(events) <= 676 else 3

        self.list_tag_to_id.setdefault("next", {})
        yr_mnth_to_events = {}

        # for start_ts, end_ts, type, name, id in events:
        for id, name, description, type, start_ts in events:
            start_dt = datetime.fromtimestamp(start_ts)
            # log_msg(f"Week details {name = }, {start_dt = }, {end_dt = }")
            monthday = start_dt.strftime("%d")
            # start_end = f"{start_dt.strftime('%-d %H:%M'):>8}"
            start_end = f"{format_hours_mins(start_dt, HRS_MINS):>8}"
            type_color = TYPE_TO_COLOR[type]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            row = [
                id,
                f"[{type_color}]{type} {escaped_start_end:<12}  {name}[/{type_color}]",
            ]
            yr_mnth_to_events.setdefault(start_dt.strftime("%y-%m"), []).append(row)

        indx = 0

        tag = indx_to_tag(indx, self.afill)

        for ym, events in yr_mnth_to_events.items():
            if events:
                details.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]"
                )
                for event in events:
                    event_id, event_str = event
                    # log_msg(f"{event_str = }")
                    tag = indx_to_tag(indx, self.afill)
                    self.list_tag_to_id["next"][tag] = event_id
                    details.append(f"  [dim]{tag}[/dim]  {event_str}")
                    indx += 1
        # NOTE: maybe return list for scrollable view?
        # details_str = "\n".join(details)
        return details

    def get_last(self):
        """
        Fetch and format details for the next instances.
        """
        events = self.db_manager.get_last_instances()
        header = f"Last instances ({len(events)})"
        # details = [f"[not bold][{HEADER_COLOR}]{header}[/{HEADER_COLOR}][/not bold]"]
        details = [header]

        if not events:
            details.append(f" [{HEADER_COLOR}]Nothing found[/{HEADER_COLOR}]")
            # return "\n".join(details)
            return details

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.afill = 1 if len(events) <= 26 else 2 if len(events) <= 676 else 3

        self.list_tag_to_id.setdefault("last", {})
        yr_mnth_to_events = {}

        # for start_ts, end_ts, type, name, id in events:
        for id, name, description, type, start_ts in events:
            start_dt = datetime.fromtimestamp(start_ts)
            # log_msg(f"Week details {name = }, {start_dt = }, {end_dt = }")
            monthday = start_dt.strftime("%d")
            # start_end = f"{start_dt.strftime('%-d %H:%M'):>8}"
            start_end = f"{format_hours_mins(start_dt, HRS_MINS):>8}"
            type_color = TYPE_TO_COLOR[type]
            escaped_start_end = f"[not bold]{start_end}[/not bold]"
            row = [
                id,
                f"[{type_color}]{type} {escaped_start_end:<12}  {name}[/{type_color}]",
            ]
            yr_mnth_to_events.setdefault(start_dt.strftime("%y-%m"), []).append(row)

        indx = 0

        tag = indx_to_tag(indx, self.afill)

        for ym, events in yr_mnth_to_events.items():
            if events:
                details.append(
                    # f" [bold][yellow]{day.strftime('%A, %B %-d')}[/yellow][/bold]"
                    f"[not bold][{HEADER_COLOR}]{ym}[/{HEADER_COLOR}][/not bold]"
                )
                for event in events:
                    event_id, event_str = event
                    # log_msg(f"{event_str = }")
                    tag = indx_to_tag(indx, self.afill)
                    self.list_tag_to_id["last"][tag] = event_id
                    details.append(f"  [dim]{tag}[/dim]  {event_str}")
                    indx += 1
        # NOTE: maybe return list for scrollable view?
        # details_str = "\n".join(details)
        return details

    def find_records(self, search_str: str):
        """
        Fetch and format details for the next instances.
        """
        events = self.db_manager.find_records(search_str)
        header = f"Items containg a match for [{SELECTED_COLOR}]{search_str}[/{SELECTED_COLOR}] ({len(events)})"
        # details = [f"[not bold][{HEADER_COLOR}]{header}[/{HEADER_COLOR}][/not bold]"]
        details = [header]

        if not events:
            details.append(f" [{HEADER_COLOR}]Nothing found[/{HEADER_COLOR}]")
            # return "\n".join(details)
            return details

        # use a, ..., z if len(events) <= 26 else use aa, ..., zz
        self.afill = 1 if len(events) <= 26 else 2 if len(events) <= 676 else 3

        self.list_tag_to_id.setdefault("find", {})

        indx = 0

        tag = indx_to_tag(indx, self.afill)
        # for start_ts, end_ts, type, name, id in events:
        for id, name, _, type, last_ts, next_ts in events:
            name = f"{truncate_string(name, 30):<30}"
            last_dt = (
                datetime.fromtimestamp(last_ts).strftime("%y-%m-%d %H:%M")
                if last_ts
                else "~"
            )
            last_fmt = f"{last_dt:^14}"
            next_dt = (
                datetime.fromtimestamp(next_ts).strftime("%y-%m-%d %H:%M")
                if next_ts
                else "~"
            )
            next_fmt = f"{next_dt:^14}"
            # yy-mm-dd hh:mm
            # log_msg(f"Week details {name = }, {start_dt = }, {end_dt = }")
            type_color = TYPE_TO_COLOR[type]
            escaped_last = f"[not bold]{last_fmt}[/not bold]"
            escaped_next = f"[not bold]{next_fmt}[/not bold]"
            row = f"[{type_color}]{type} {name} {escaped_last} {escaped_next}[/{type_color}]"
            tag = indx_to_tag(indx, self.afill)
            self.list_tag_to_id["find"][tag] = id
            details.append(f"  [dim]{tag}[/dim]  {row}")
            indx += 1
        # NOTE: maybe return list for scrollable view?
        # details_str = "\n".join(details)
        return details
