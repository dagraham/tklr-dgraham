from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Tuple


def group_events_by_date(events: List[Tuple[float, str]]) -> dict:
    """
    Groups events by date.
    Each event is a tuple of (timestamp, description).
    Returns a dict of date -> List of event strings.
    """
    grouped = defaultdict(list)
    for timestamp, description in events:
        dt = datetime.fromtimestamp(timestamp)
        grouped[dt.date()].append((dt.time(), description))
    return dict(grouped)


def paginate_events_by_line_count(
    grouped_events: dict,
    max_lines_per_page: int,
    today: datetime.date,
) -> List[List[Tuple[str, List[str], bool]]]:
    """
    Splits grouped events into paginated pages with optional continuation flags.
    Each page is a list of (header_line, event_lines, is_continued).
    """
    pages = []
    current_page = []
    current_line_count = 0
    split_buffer = []

    sorted_dates = sorted(grouped_events.keys())
    i = 0
    while i < len(sorted_dates):
        date = sorted_dates[i]
        events = grouped_events[date]
        day_lines = len(events) + 1  # +1 for header

        if day_lines + current_line_count <= max_lines_per_page:
            # Fits completely
            header = f"{format_day_header(date, today)}"
            event_lines = [format_event_line(t, d) for t, d in events]
            current_page.append((header, event_lines, False))
            current_line_count += day_lines
            i += 1
        elif current_line_count == 0:
            # Day doesn't fit and we're at the top of the page, so split
            lines_remaining = max_lines_per_page - 2  # room for header and 'continues'
            split_header = f"{format_day_header(date, today)}"
            part_lines = [format_event_line(t, d) for t, d in events[:lines_remaining]]
            part_lines.append("  ↪ [dim][continues on next page][/dim]")
            current_page.append((split_header, part_lines, True))

            # Store remainder for next round
            grouped_events[date] = events[lines_remaining:]
            pages.append(current_page)
            current_page = []
            current_line_count = 0
        else:
            # Day doesn't fit, defer to next page
            pages.append(current_page)
            current_page = []
            current_line_count = 0

    if current_page:
        pages.append(current_page)
    return pages


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


# Demo generation for testing
now = datetime.now()
mock_events = []
for i in range(30):
    day_offset = i // 5
    time_of_day = timedelta(hours=(i % 5) * 2 + 9)
    dt = now + timedelta(days=day_offset) + time_of_day
    mock_events.append((dt.timestamp(), f"Event #{i + 1}"))

grouped = group_events_by_date(mock_events)
pages = paginate_events_by_line_count(grouped, max_lines_per_page=12, today=now.date())


import rich
from rich.console import Console
from rich.panel import Panel

console = Console()
for page_num, page in enumerate(pages):
    console.rule(f"Events Page {page_num + 1}")
    for header, events, continued in page:
        header_text = f"{header} — continued" if continued else header
        console.print(f"[bold]{header_text}[/bold]")
        for line in events:
            console.print("  " + line)
    console.print()


from datetime import datetime, timedelta
from collections import defaultdict
from typing import List, Tuple
from itertools import product
from string import ascii_lowercase

from rich.console import Console

console = Console()


def group_events_by_date(events: List[Tuple[float, str]]) -> dict:
    grouped = defaultdict(list)
    for timestamp, description in events:
        dt = datetime.fromtimestamp(timestamp)
        grouped[dt.date()].append((dt.time(), description))
    return dict(grouped)


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


def paginate_events_by_line_count(
    grouped_events: dict,
    max_lines_per_page: int,
    today: datetime.date,
) -> List[List[Tuple[str, List[str], bool]]]:
    pages = []
    current_page = []
    current_line_count = 0

    sorted_dates = sorted(grouped_events.keys())
    i = 0
    while i < len(sorted_dates):
        date = sorted_dates[i]
        events = grouped_events[date]
        day_lines = len(events) + 1

        if day_lines + current_line_count <= max_lines_per_page:
            header = f"{format_day_header(date, today)}"
            event_lines = [format_event_line(t, d) for t, d in events]
            current_page.append((header, event_lines, False))
            current_line_count += day_lines
            i += 1
        elif current_line_count == 0:
            lines_remaining = max_lines_per_page - 2
            split_header = f"{format_day_header(date, today)}"
            part_lines = [format_event_line(t, d) for t, d in events[:lines_remaining]]
            part_lines.append("↪ [dim][continues on next page][/dim]")
            current_page.append((split_header, part_lines, True))
            grouped_events[date] = events[lines_remaining:]
            pages.append(current_page)
            current_page = []
            current_line_count = 0
        else:
            pages.append(current_page)
            current_page = []
            current_line_count = 0

    if current_page:
        pages.append(current_page)
    return pages


def generate_tags():
    for length in range(1, 3):
        for combo in product(ascii_lowercase, repeat=length):
            yield "".join(combo)


def tag_paginated_events(pages):
    tagged_pages = []
    for page in pages:
        tag_gen = generate_tags()
        tagged_page = []
        for header, events, continued in page:
            tagged_events = []
            for line in events:
                if line.strip().startswith("↪"):
                    tagged_events.append(("", line))
                else:
                    tag = next(tag_gen)
                    tagged_events.append((tag, line))
            header_text = f"{header} — continued" if continued else header
            tagged_page.append((header_text, tagged_events))
        tagged_pages.append(tagged_page)
    return tagged_pages


def paginate_urgency_tasks(tasks, tasks_per_page=10):
    pages = []
    tag_gen = generate_tags()
    current_page = []
    for i, (urgency, desc) in enumerate(tasks):
        if i % tasks_per_page == 0:
            if current_page:
                pages.append(current_page)
            current_page = []
            tag_gen = generate_tags()
        tag = next(tag_gen)
        current_page.append((tag, urgency, desc))
    if current_page:
        pages.append(current_page)
    return pages


# Generate sample event data
now = datetime.now()
mock_events = []
for i in range(30):
    day_offset = i // 5
    time_of_day = timedelta(hours=(i % 5) * 2 + 9)
    dt = now + timedelta(days=day_offset) + time_of_day
    mock_events.append((dt.timestamp(), f"Event #{i + 1}"))

grouped = group_events_by_date(mock_events)
event_pages = paginate_events_by_line_count(
    grouped, max_lines_per_page=12, today=now.date()
)
tagged_event_pages = tag_paginated_events(event_pages)

# Generate sample urgency tasks
urgency_tasks = [(95 - i * 3, f"Urgent task #{i + 1}") for i in range(25)]
urgency_pages = paginate_urgency_tasks(urgency_tasks, tasks_per_page=7)

# Display first page of tagged events
console.rule("Tagged Events Page 1")
for header, events in tagged_event_pages[0]:
    console.print(f"[bold]{header}[/bold]")
    for tag, line in events:
        if tag:
            console.print(f"  {tag}  {line}")
        else:
            console.print("     " + line)

# Display first page of urgency tasks
console.rule("Urgency Tasks Page 1")
for tag, urgency, desc in urgency_pages[0]:
    color = "red" if urgency > 90 else "yellow" if urgency > 70 else "green"
    console.print(f"  {tag}  [{color}]{urgency:3.0f}[/{color}] {desc}")
