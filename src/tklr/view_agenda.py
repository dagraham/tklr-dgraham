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

# from tklr.model import UrgencyCalulator
from .shared import log_msg, display_messages

# env = TklrEnvironment()

# urgency = env.config.urgency

HIGHLIGHT = "#6495ED"
# name_style = Style(color=hex_val)
# HIGHLIGHT_STYLE = Style(color=get_contrasting_text_color(HIGHLIGHT), bgcolor=HIGHLIGHT)
HEADER = "#FFF8DC"
TASK = "#87CEFA"
EVENT = "#32CD32"
BEGIN = "#FFD700"
DRAFT = "#FFA07A"


def run_agenda_view(controller):
    now = datetime.now()
    console = Console()
    width, height = console.size
    max_lines_per_page = (height - 1) // 2 - 2  # split screen assumption

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
        label = f"[{HEADER}][not bold]{dtstr}[/not bold] (Today)[/{HEADER}]"
    elif date == tomorrow:
        label = f"[{HEADER}][not bold]{dtstr}[/not bold] (Tomorrow)[/{HEADER}]"
    else:
        label = f"[{HEADER}][not bold]{dtstr}[/not bold][/{HEADER}]"
    return label


def paginate_events_by_line_count(events_by_date, max_lines_per_page, today):
    from copy import deepcopy

    def format_event_line(label, subject):
        return f"[not bold]{label}[/not bold] {subject}" if label.strip() else subject

    def calculate_padding(lines_used):
        log_msg(f"{max_lines_per_page = }, {lines_used = }")
        return max(0, max_lines_per_page - lines_used)

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

        lines = []
        continued = False
        available_lines = max_lines_per_page

        if len(events) > available_lines:
            # Avoid showing lonely header
            if available_lines < 2:
                if current_page:
                    # Pad if needed
                    pad = calculate_padding(current_line_count)
                    if pad:
                        current_page.append(("", [""] * pad, False))
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
        else:
            lines = [format_event_line(label, subject) for label, subject, _ in events]
            carryover = None
            continued = False
            i += 1

        current_page.append((header, lines, continued))
        current_line_count += len(lines) + 1  # +1 for header

        if current_line_count >= max_lines_per_page:
            pages.append(current_page)
            current_page = []
            current_line_count = 0

    # Final page padding
    if current_page:
        current_line_count = sum(len(lines) + 1 for _, lines, _ in current_page)
        pad = calculate_padding(current_line_count)
        if pad:
            current_page.append(("", [""] * pad, False))
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
    for i, (urgency, color, subject, id, job) in enumerate(
        tasks
    ):  # (urgency, subject, record_id, job_id)
        if i % per_page == 0 and current_page:
            pages.append(current_page)
            current_page = []
            tag_gen = generate_tags()
        tag = next(tag_gen)
        current_page.append((tag, urgency, color, subject, id, job))
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
            else f"[{HEADER}]{event_title}[/]"
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
            else f"[{HEADER}]{task_title}[/]"
        )
        for tag, urgency, color, subject, id, job in task_pages[task_page]:
            console.print(
                f"  [dim]{tag}[/dim]  [not bold][{color}]{str(round(urgency * 100)):>2}[/{color}] [{TASK}]{subject} [dim]{id} {job if job else ''}[/dim][/{TASK}][/not bold]"
            )

        console.print("\n[dim]←/→ switch page; ↑/↓ switch pane; Q to quit[/dim]")

        keypress = readchar.readkey()
        if keypress == "Q":
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
