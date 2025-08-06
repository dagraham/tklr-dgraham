# agenda_demo.py
from datetime import datetime, timedelta
from collections import defaultdict
from itertools import product
from string import ascii_lowercase
from rich.console import Console
import readchar
from readchar import key
import copy


def generate_long_day_events(now, count=24):
    events = []
    for i in range(count):
        dt = now.replace(hour=8, minute=0) + timedelta(hours=i)
        events.append((dt.timestamp(), f"LongDay Event #{i + 1}"))
    return events


def generate_mock_tasks(count=25):
    return [(95 - i * 3, f"Urgent task #{i + 1}") for i in range(count)]


def group_events_by_date(events):
    grouped = defaultdict(list)
    for ts, desc in events:
        dt = datetime.fromtimestamp(ts)
        grouped[dt.date()].append((dt.time(), desc))
    return dict(grouped)


def generate_tags():
    for length in range(1, 3):
        for combo in product(ascii_lowercase, repeat=length):
            yield "".join(combo)


def format_day_header(date, today):
    dtstr = date.strftime("%a %b %d")
    tomorrow = today + timedelta(days=1)
    if date == today:
        label = f"{dtstr} (Today)"
    elif date == tomorrow:
        label = f"{dtstr} (Tomorrow)"
    else:
        label = f"{dtstr}"
    return label


def format_event_line(t, d):
    return f"{t.strftime('%-I:%M%p').lower()}  {d}"


# def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
#     grouped_events = copy.deepcopy(grouped_events_original)
#     pages = []
#     current_page = []
#     current_line_count = 0
#     sorted_dates = sorted(grouped_events.keys())
#     i = 0
#     while i < len(sorted_dates):
#         date = sorted_dates[i]
#         events = grouped_events[date]
#         day_lines = len(events) + 1
#         if day_lines + current_line_count <= max_lines_per_page:
#             header = format_day_header(date, today)
#             lines = [format_event_line(t, d) for t, d in events]
#             current_page.append((header, lines, False))
#             current_line_count += day_lines
#             i += 1
#         elif current_line_count == 0:
#             rem = max_lines_per_page - 2
#             header = format_day_header(date, today)
#             lines = [format_event_line(t, d) for t, d in events[:rem]]
#             lines.append("↪ [dim]continues on next page[/dim]")
#             current_page.append((header, lines, True))
#             grouped_events[date] = events[rem:]
#             pages.append(current_page)
#             current_page = []
#             current_line_count = 0
#         else:
#             pages.append(current_page)
#             current_page = []
#             current_line_count = 0
#     if current_page:
#         pages.append(current_page)
#     return pages
#


def paginate_events_by_line_count(grouped_events_original, max_lines_per_page, today):
    grouped_events = copy.deepcopy(grouped_events_original)
    pages = []
    current_page = []
    current_line_count = 0
    sorted_dates = sorted(grouped_events.keys())
    i = 0
    carryover = None
    carryover_events = None
    carryover_heading = ""

    while i < len(sorted_dates) or carryover:
        if carryover:
            date = carryover
            events = carryover_events
            header = f"{format_day_header(date, today)}{carryover_heading}"
        else:
            date = sorted_dates[i]
            events = grouped_events[date]
            header = f"{format_day_header(date, today)}{carryover_heading}"

        # How many event lines can we show on this page?
        available_lines = (
            max_lines_per_page - 2
        )  # 1 for header, 1 for continuation line
        if len(events) > available_lines:
            # Split this day again
            visible = events[:available_lines]
            remaining = events[available_lines:]

            lines = [format_event_line(t, d) for t, d in visible]
            lines.append("↪ [dim]continues on next page[/dim]")

            current_page.append((header, lines, True))
            pages.append(current_page)
            current_page = []
            current_line_count = 0

            carryover = date
            carryover_events = remaining
            carryover_heading = " - continued"
        else:
            # Whole day fits, or remainder of a split day fits
            lines = [format_event_line(t, d) for t, d in events]
            current_page.append((header, lines, False))
            carryover = None
            carryover_events = None
            carryover_heading = ""
            i += 1

            current_line_count += len(lines) + 1  # header + lines
            if current_line_count >= max_lines_per_page:
                pages.append(current_page)
                current_page = []
                current_line_count = 0

    if current_page:
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
                tag = "" if line.startswith("↪") else next(tag_gen)
                tagged_events.append((tag, line))
            tagged_page.append((header, tagged_events))
        tagged.append(tagged_page)
    return tagged


def paginate_urgency_tasks(tasks, per_page=10):
    pages = []
    tag_gen = generate_tags()
    current_page = []
    for i, (urgency, desc) in enumerate(tasks):
        if i % per_page == 0 and current_page:
            pages.append(current_page)
            current_page = []
            tag_gen = generate_tags()
        tag = next(tag_gen)
        current_page.append((tag, urgency, desc))
    if current_page:
        pages.append(current_page)
    return pages


def agenda_navigation_loop(event_pages, task_pages):
    console = Console()
    total_event_pages = len(event_pages)
    total_task_pages = len(task_pages)
    event_page = 0
    task_page = 0

    while True:
        console.clear()
        console.rule(f"Events (Page {event_page + 1} of {total_event_pages})")
        for header, events in event_pages[event_page]:
            console.print(f"[bold]{header}[/bold]")
            for tag, line in events:
                console.print(f"  {tag}  {line}" if tag else f"     {line}")

        console.rule(f"Tasks (Page {task_page + 1} of {total_task_pages})")
        for tag, urgency, desc in task_pages[task_page]:
            color = "red" if urgency > 90 else "yellow" if urgency > 70 else "green"
            console.print(f"  {tag}  [{color}]{urgency:3.0f}[/{color}] {desc}")

        console.print(
            "\n[dim]←/→ to scroll event pages, ↑/↓ for tasks, q to quit[/dim]"
        )
        keypress = readchar.readkey()
        if keypress == "q":
            break
        elif keypress == key.RIGHT and event_page < total_event_pages - 1:
            event_page += 1
        elif keypress == key.LEFT and event_page > 0:
            event_page -= 1
        elif keypress == key.DOWN and task_page < total_task_pages - 1:
            task_page += 1
        elif keypress == key.UP and task_page > 0:
            task_page -= 1


if __name__ == "__main__":
    now = datetime.now()
    events = generate_long_day_events(now, count=24)
    tasks = generate_mock_tasks()

    grouped = group_events_by_date(events)
    # event_pages = paginate_events_by_line_count(
    #     grouped, max_lines_per_page=10, today=now.date()
    # )
    console = Console()
    _, terminal_height = console.size

    # Estimate:
    #  - 2 lines for Rich rules
    #  - 1 line for spacing below tasks
    #  - ~2 lines for the prompt/legend
    #  - Half the rest goes to events
    usable_lines = terminal_height - 6
    max_lines_per_page = usable_lines // 2

    event_pages = paginate_events_by_line_count(
        grouped, max_lines_per_page=max_lines_per_page, today=now.date()
    )
    tagged_event_pages = tag_paginated_events(event_pages)
    urgency_pages = paginate_urgency_tasks(tasks, per_page=max_lines_per_page)

    agenda_navigation_loop(tagged_event_pages, urgency_pages)
