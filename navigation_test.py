from datetime import datetime, timedelta
from collections import defaultdict
from itertools import product
from string import ascii_lowercase
from rich.console import Console
import readchar
from readchar import key

# ========== MOCK DATA ==========


def generate_mock_events(now: datetime, count: int = 30):
    # events = []
    # for i in range(count):
    #     day_offset = i // 5
    #     time_of_day = timedelta(hours=(i % 5) * 2 + 9)
    #     dt = now + timedelta(days=day_offset) + time_of_day
    #     events.append((dt.timestamp(), f"Event #{i + 1}"))
    events = []
    for i in range(24):  # 24 events on the same day, one per hour
        dt = now.replace(hour=8, minute=0, second=0, microsecond=0) + timedelta(hours=i)
        events.append((dt.timestamp(), f"LongDay Event #{i + 1}"))
    return events


def generate_mock_tasks(count: int = 25):
    return [(95 - i * 3, f"Urgent task #{i + 1}") for i in range(count)]


# ========== UTILS ==========


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
    label = "Today" if date == today else date.strftime("%a %b %d")
    return label


def format_event_line(t, d):
    return f"{t.strftime('%-I:%M%p').lower()}  {d}"


def paginate_events_by_line_count(grouped_events, max_lines_per_page, today):
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
            header = format_day_header(date, today)
            lines = [format_event_line(t, d) for t, d in events]
            current_page.append((header, lines, False))
            current_line_count += day_lines
            i += 1
        elif current_line_count == 0:
            rem = max_lines_per_page - 2
            header = format_day_header(date, today)
            lines = [format_event_line(t, d) for t, d in events[:rem]]
            lines.append("↪ [dim][continues on next page][/dim]")
            current_page.append((header, lines, True))
            grouped_events[date] = events[rem:]
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
            hdr = f"{header} — continued" if continued else header
            tagged_page.append((hdr, tagged_events))
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


# ========== INTERACTIVE LOOP ==========


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


# ========== MAIN ==========

if __name__ == "__main__":
    now = datetime.now()
    events = generate_mock_events(now)
    tasks = generate_mock_tasks()

    grouped = group_events_by_date(events)
    event_pages = paginate_events_by_line_count(
        grouped, max_lines_per_page=12, today=now.date()
    )
    tagged_event_pages = tag_paginated_events(event_pages)
    urgency_pages = paginate_urgency_tasks(tasks, per_page=7)

    agenda_navigation_loop(tagged_event_pages, urgency_pages)
