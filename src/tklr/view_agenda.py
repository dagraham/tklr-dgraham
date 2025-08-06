from datetime import datetime, timedelta
from collections import defaultdict
from itertools import product
from string import ascii_lowercase
from rich.console import Console
import readchar
from readchar import key
import copy
from typing import List, Tuple

from rich.style import Style
from colorsys import rgb_to_hls
from tklr.tklr_env import TklrEnvironment

env = TklrEnvironment()

# urgency = env.config.urgency
MIN_HEX_COLOR = env.config.urgency.colors.min_hex_color
MAX_HEX_COLOR = env.config.urgency.colors.max_hex_color
STEPS = env.config.urgency.colors.steps


HIGHLIGHT = "#6495ED"
# name_style = Style(color=hex_val)
# HIGHLIGHT_STYLE = Style(color=get_contrasting_text_color(HIGHLIGHT), bgcolor=HIGHLIGHT)
HEADER = "#FFF8DC"
TASK = "#87CEFA"
EVENT = "#32CD32"
BEGIN = "#FFD700"
DRAFT = "#FFA07A"


def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    hex_color = hex_color.lstrip("#")
    return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))


def rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def get_urgency_color_buckets(neg_hex: str, max_hex: str, steps: int = 10) -> List[str]:
    neg_rgb = hex_to_rgb(neg_hex)
    max_rgb = hex_to_rgb(max_hex)

    buckets = []
    for i in range(steps):
        t = i / (steps - 1)
        rgb = tuple(
            round(neg + t * (maxc - neg)) for neg, maxc in zip(neg_rgb, max_rgb)
        )
        buckets.append(rgb_to_hex(rgb))
    return buckets


BUCKETS = get_urgency_color_buckets(MIN_HEX_COLOR, MAX_HEX_COLOR, STEPS)


def urgency_to_bucket_color(urgency: float) -> str:
    if urgency <= 0.0:
        return MIN_HEX_COLOR
    if urgency >= 1.0:
        return MAX_HEX_COLOR

    i = min(int(urgency * len(BUCKETS)), len(BUCKETS) - 1)
    return BUCKETS[i]


def get_contrasting_text_color(hex_color: str) -> str:
    hex_color = hex_color.lstrip("#")
    r, g, b = [int(hex_color[i : i + 2], 16) for i in (0, 2, 4)]
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    return "black" if brightness > 128 else "white"


def run_agenda_view(controller):
    now = datetime.now()
    console = Console()
    width, height = console.size
    max_lines_per_page = height // 2 - 4  # split screen assumption

    # Get events and tasks from controller
    grouped_events = controller.get_agenda_events()  # already grouped and labeled
    tasks = controller.get_agenda_tasks()

    event_pages = paginate_events_by_line_count(
        grouped_events, max_lines_per_page, today=now.date()
    )
    tagged_event_pages = tag_paginated_events(event_pages)
    urgency_pages = paginate_urgency_tasks(tasks, per_page=max_lines_per_page)

    agenda_navigation_loop(tagged_event_pages, urgency_pages)


def generate_tags():
    for length in range(1, 3):  # a–z, aa–zz
        for combo in product(ascii_lowercase, repeat=length):
            yield "".join(combo)


def format_day_header(date, today):
    dtstr = date.strftime("%a %b %-d")
    tomorrow = today + timedelta(days=1)
    if date == today:
        label = f"[not bold]{dtstr}[/not bold] (Today)"
    elif date == tomorrow:
        label = f"[not bold]{dtstr}[/not bold] (Tomorrow)"
    else:
        label = f"[not bold]{dtstr}[/not bold]"
    return label


# def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
#     grouped_events = copy.deepcopy(grouped_events_original)
#     pages = []
#     current_page = []
#     current_line_count = 0
#     sorted_dates = sorted(grouped_events.keys())
#     i = 0
#     carryover = None
#     carryover_events = None
#     carryover_heading = ""
#
#     while i < len(sorted_dates) or carryover:
#         if carryover:
#             date = carryover
#             events = carryover_events
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#         else:
#             date = sorted_dates[i]
#             events = grouped_events[date]
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#
#         available_lines = max_lines_per_page - 2
#         if len(events) > available_lines:
#             visible = events[:available_lines]
#             remaining = events[available_lines:]
#             lines = [
#                 f"[not bold]{label} {subject} {id}[/not bold]"
#                 for label, subject, id in visible
#             ]
#             lines.append("\u21aa [dim]continues on next page[/dim]")
#             current_page.append((header, lines, True))
#             pages.append(current_page)
#             current_page = []
#             current_line_count = 0
#             carryover = date
#             carryover_events = remaining
#             carryover_heading = " - continued"
#         else:
#             lines = [
#                 f"[not bold]{label} {subject} {id}[/not bold]"
#                 for label, subject, id in events
#             ]
#             current_page.append((header, lines, False))
#             carryover = None
#             carryover_events = None
#             carryover_heading = ""
#             i += 1
#
#             current_line_count += len(lines) + 1
#             if current_line_count >= max_lines_per_page:
#                 pages.append(current_page)
#                 current_page = []
#                 current_line_count = 0
#
#     if current_page:
#         pages.append(current_page)
#
#     return pages


# def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
#     grouped_events = copy.deepcopy(grouped_events_original)
#     pages = []
#     current_page = []
#     current_line_count = 0
#     sorted_dates = sorted(grouped_events.keys())
#     i = 0
#     carryover = None
#     carryover_events = None
#     carryover_heading = ""
#
#     while i < len(sorted_dates) or carryover:
#         if carryover:
#             date = carryover
#             events = carryover_events
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#         else:
#             date = sorted_dates[i]
#             events = grouped_events[date]
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#
#         available_lines = max_lines_per_page - 2  # 1 for header, 1 for continuation
#         if len(events) > available_lines:
#             visible = events[:available_lines]
#             remaining = events[available_lines:]
#             lines = [format_event_line(t, d) for t, d in visible]
#             lines.append("\u21aa [dim]continues on next page[/dim]")
#             current_page.append((header, lines, True))
#             pages.append(current_page)
#             current_page = []
#             carryover = date
#             carryover_events = remaining
#             carryover_heading = " - continued"
#         else:
#             lines = [format_event_line(t, d) for t, d in events]
#             # 🟡 Pad with blank lines to maintain consistent height
#             used_lines = len(lines) + 1  # +1 for the header
#             padding_needed = max_lines_per_page - used_lines
#             lines.extend([""] * padding_needed)
#
#             current_page.append((header, lines, False))
#             carryover = None
#             carryover_events = None
#             carryover_heading = ""
#             i += 1
#
#             current_line_count += used_lines
#             if current_line_count >= max_lines_per_page:
#                 pages.append(current_page)
#                 current_page = []
#                 current_line_count = 0
#
#     if current_page:
#         pages.append(current_page)
#
#     return pages


# def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
#     import copy
#
#     grouped_events = copy.deepcopy(grouped_events_original)
#     pages = []
#     current_page = []
#     current_line_count = 0
#     sorted_dates = sorted(grouped_events.keys())
#     i = 0
#     carryover = None
#     carryover_events = None
#     carryover_heading = ""
#
#     while i < len(sorted_dates) or carryover:
#         if carryover:
#             date = carryover
#             events = carryover_events
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#         else:
#             date = sorted_dates[i]
#             events = grouped_events[date]
#             header = f"{format_day_header(date, today)}"
#
#         # Account for header line
#         needed_lines = 1 + len(events)
#
#         # If too many events for current page
#         if needed_lines > max_lines_per_page:
#             # Avoid splitting if only 1 event remains
#             available_lines = (
#                 max_lines_per_page - 2
#             )  # 1 for header, 1 for continuation line
#             if len(events) > available_lines + 1:
#                 visible = events[:available_lines]
#                 remaining = events[available_lines:]
#                 lines = [format_event_line(t, d) for t, d in visible]
#                 lines.append("\u21aa [dim]continues on next page[/dim]")
#                 current_page.append((header + carryover_heading, lines, True))
#                 carryover = date
#                 carryover_events = remaining
#                 carryover_heading = " - continued"
#                 i = i if carryover else i + 1
#             else:
#                 # Don't split; just include all remaining
#                 lines = [format_event_line(t, d) for t, d in events]
#                 current_page.append((header + carryover_heading, lines, False))
#                 carryover = None
#                 carryover_events = None
#                 carryover_heading = ""
#                 i += 1
#         else:
#             lines = [format_event_line(t, d) for t, d in events]
#             current_page.append((header + carryover_heading, lines, False))
#             carryover = None
#             carryover_events = None
#             carryover_heading = ""
#             i += 1
#
#         # Tally up how many lines would be printed on the page
#         flat_count = sum(1 + len(lines) for _, lines, _ in current_page)
#         if flat_count >= max_lines_per_page or i >= len(sorted_dates):
#             # Add padding if short
#             padding_needed = max_lines_per_page - flat_count
#             if padding_needed > 0:
#                 current_page.append(("", [""] * padding_needed, False))
#             pages.append(current_page)
#             current_page = []
#
#     return pages
#
#
# def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
#     import copy
#
#     grouped_events = copy.deepcopy(grouped_events_original)
#     pages = []
#     current_page = []
#     current_line_count = 0
#     sorted_dates = sorted(grouped_events.keys())
#     i = 0
#     carryover = None
#     carryover_events = None
#     carryover_heading = ""
#
#     while i < len(sorted_dates) or carryover:
#         if carryover:
#             date = carryover
#             events = carryover_events
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#         else:
#             date = sorted_dates[i]
#             events = grouped_events[date]
#             header = f"{format_day_header(date, today)}{carryover_heading}"
#
#         lines = [
#             f"[not bold]{label} {subject} {id}[/not bold]"
#             for label, subject, id in events
#         ]
#
#         total_lines = len(lines) + 1  # +1 for the header line
#
#         if total_lines + current_line_count <= max_lines_per_page:
#             # Whole day fits
#             current_page.append((header, lines, False))
#             current_line_count += total_lines
#             carryover = None
#             carryover_events = None
#             carryover_heading = ""
#             i += 1
#         else:
#             # Need to split this day across pages
#             available_event_lines = (
#                 max_lines_per_page - current_line_count - 2
#             )  # 1 for header, 1 for continuation
#             visible = events[:available_event_lines]
#             remaining = events[available_event_lines:]
#
#             visible_lines = [
#                 f"{label} {subject} {id}" for label, subject, id in visible
#             ]
#             # visible_lines = [format_event_line(label, subject) for label, subject, _ in visible]
#             visible_lines.append("\u21aa [dim]continues on next page[/dim]")
#
#             current_page.append((header + carryover_heading, visible_lines, True))
#             pages.append(current_page)
#
#             current_page = []
#             current_line_count = 0
#
#             carryover = date
#             carryover_events = remaining
#             carryover_heading = " - continued"
#
#     if current_page:
#         pages.append(current_page)
#
#     return pages
#


def paginate_events_by_line_count(events_by_date, max_lines_per_page, today):
    from copy import deepcopy

    def format_day_header(date, today):
        dtstr = date.strftime("%a %b %-d")
        tomorrow = today + timedelta(days=1)
        if date == today:
            label = f"{dtstr} (Today)"
        elif date == tomorrow:
            label = f"{dtstr} (Tomorrow)"
        else:
            label = dtstr
        return label

    def format_event_line(label, subject):
        # return f"{label:>5} {subject}"
        return f"{label:>5} {subject}"

    def calculate_padding(lines_used, max_lines):
        return max(0, max_lines - lines_used)

    grouped = deepcopy(events_by_date)
    sorted_dates = sorted(grouped.keys())

    pages = []
    current_page = []
    current_line_count = 0
    i = 0
    carryover = None

    while i < len(sorted_dates) or carryover:
        if carryover:
            date, events = carryover
            header = f"{format_day_header(date, today)} - continued"
        else:
            date = sorted_dates[i]
            events = grouped[date]
            header = format_day_header(date, today)

        available_lines = max_lines_per_page - 1  # minus header
        lines = []
        continued = False

        if len(events) > available_lines:
            # Avoid showing lonely header
            if available_lines < 2:
                # Skip this day for now, try again on next page
                if current_page:
                    pages.append(current_page)
                    current_page = []
                    current_line_count = 0
                carryover = (date, events)
                continue

            visible = events[: available_lines - 1]
            remaining = events[available_lines - 1 :]
            lines = [format_event_line(label, subject) for label, subject, _ in visible]
            lines.append("\u21aa [dim]continues on next page[/dim]")
            continued = True
            carryover = (date, remaining)
            i += 0  # retry this date next loop
        else:
            lines = [format_event_line(label, subject) for label, subject, _ in events]
            carryover = None
            continued = False
            i += 1

        # Add header and lines to page
        current_page.append((header, lines, continued))
        current_line_count += len(lines) + 1  # +1 for header
        # if current_line_count > max_lines_per_page - 1:
        #     lines_to_pad = calculate_padding(current_line_count, max_lines_per_page)
        #     if lines_to_pad:
        #         current_page.append(("", [""] * lines_to_pad, False))
        #     pages.append(current_page)
        #     current_page = []
        #     current_line_count = 0

        if current_line_count >= max_lines_per_page:
            # Pad this page if it's short
            lines_to_pad = calculate_padding(current_line_count, max_lines_per_page)
            if lines_to_pad:
                current_page.append(("", [""] * lines_to_pad, False))
            pages.append(current_page)
            current_page = []
            current_line_count = 0

    if current_page:
        # Final page padding
        current_line_count = sum(len(lines) + 1 for _, lines, _ in current_page)
        lines_to_pad = calculate_padding(current_line_count, max_lines_per_page)
        if lines_to_pad:
            current_page.append(("", [""] * lines_to_pad, False))
        pages.append(current_page)

    return pages


def tag_paginated_events(pages):
    tagged = []
    for page in pages:
        tag_gen = generate_tags()
        tagged_page = []
        for header, events, continued in page:
            tagged_events = []
            for line in events:
                if line.startswith("\u21aa") or not line.strip():
                    tag = ""
                else:
                    tag = next(tag_gen)
                tagged_events.append((tag, line))
            hdr = header
            tagged_page.append((hdr, tagged_events))
        tagged.append(tagged_page)
    return tagged


def paginate_urgency_tasks(tasks, per_page=10):
    pages = []
    current_page = []
    tag_gen = generate_tags()
    for i, (urgency, subject, id, job) in enumerate(
        tasks
    ):  # (urgency, subject, record_id, job_id)
        if i % per_page == 0 and current_page:
            pages.append(current_page)
            current_page = []
            tag_gen = generate_tags()
        tag = next(tag_gen)
        current_page.append((tag, urgency, subject, id, job))
    if current_page:
        pages.append(current_page)
    return pages


def agenda_navigation_loop(event_pages, task_pages):
    console = Console()
    total_event_pages = len(event_pages)
    total_task_pages = len(task_pages)
    event_page = 0
    task_page = 0
    active_pane = "events"

    while True:
        console.clear()
        event_title = f" Events (Page {event_page + 1} of {total_event_pages}) "
        task_title = f" Tasks (Page {task_page + 1} of {total_task_pages}) "

        console.rule(
            f"[bold black on {HIGHLIGHT}]{event_title}[/]"
            if active_pane == "events"
            else event_title
        )
        for header, events in event_pages[event_page]:
            console.print(f"[{HEADER}]{header}[/{HEADER}]")
            for tag, line in events:
                console.print(
                    f"  [dim]{tag}[/dim]  [{EVENT}]{line}[/{EVENT}]"
                    if tag
                    else f"     {line}"
                )

        console.rule(
            f"[bold black on {HIGHLIGHT}]{task_title}[/]"
            if active_pane == "tasks"
            else task_title
        )
        for tag, urgency, subject, id, job in task_pages[task_page]:
            console.print(
                f"  [dim]{tag}[/dim]  [not bold][{urgency_to_bucket_color(urgency)}]{str(round(urgency * 100))}[/{urgency_to_bucket_color(urgency)}] [{TASK}]{subject} [dim]{id} {job if job else ''}[/dim][/{TASK}][/not bold]"
            )

        console.print("\n[dim]←/→ switch page; ↑/↓ switch pane; q to quit[/dim]")

        keypress = readchar.readkey()
        if keypress == "q":
            break
        elif keypress == key.UP or keypress == key.DOWN:
            active_pane = "events" if active_pane == "tasks" else "tasks"
        elif keypress == key.RIGHT:
            if active_pane == "events" and event_page < total_event_pages - 1:
                event_page += 1
            elif active_pane == "tasks" and task_page < total_task_pages - 1:
                task_page += 1
        elif keypress == key.LEFT:
            if active_pane == "events" and event_page > 0:
                event_page -= 1
            elif active_pane == "tasks" and task_page > 0:
                task_page -= 1
