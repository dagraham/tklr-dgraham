import sys
import os
import click
from pathlib import Path
from rich import print
from typing import Dict, List, Tuple, Optional

from collections import defaultdict

from rich.console import Console
from rich.text import Text
# from rich.table import Table

from dateutil import parser as dt_parser

from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager
from tklr.view import DynamicViewApp
from tklr.tklr_env import TklrEnvironment
from tklr.migration import MIGRATION_ITEM_TYPES, migrate_etm_directory

# from tklr.view_agenda import run_agenda_view
from tklr.versioning import get_version
from tklr.shared import format_time_range, format_iso_week, TYPE_TO_COLOR
from tklr.query import QueryError

from datetime import date, datetime, timedelta, time


class _DateParam(click.ParamType):
    name = "date"

    def convert(self, value, param, ctx):
        if value is None:
            return None
        if isinstance(value, date):
            return value
        s = str(value).strip().lower()
        if s in ("today", "now"):
            return date.today()
        try:
            return datetime.strptime(s, "%Y-%m-%d").date()
        except Exception:
            self.fail("Expected YYYY-MM-DD or 'today'", param, ctx)


class _DateOrInt(click.ParamType):
    name = "date|int"
    _date = _DateParam()

    def convert(self, value, param, ctx):
        if value is None:
            return None
        # try int
        try:
            return int(value)
        except (TypeError, ValueError):
            pass
        # try date
        return self._date.convert(value, param, ctx)


_DATE = _DateParam()
_DATE_OR_INT = _DateOrInt()

VERSION = get_version()


def ensure_database(db_path: str, env: TklrEnvironment):
    if not Path(db_path).exists():
        print(
            f"[yellow]⚠️ [/yellow]Database not found. Creating new database at {db_path}"
        )
        dbm = DatabaseManager(db_path, env)
        dbm.setup_database()


def format_tokens(tokens, width=80):
    return " ".join([f"{t['token'].strip()}" for t in tokens])


def _plain_from_markup(text: str) -> str:
    try:
        return Text.from_markup(text).plain
    except Exception:
        return text


def _print_markup_or_plain(console: Console, text: str, rich: bool) -> None:
    if rich:
        console.print(text)
    else:
        console.print(_plain_from_markup(text), markup=False, highlight=False)


def _print_detail_lines(console: Console, lines: list[str], rich: bool) -> None:
    last_was_blank = False
    for line in lines:
        plain = _plain_from_markup(line)
        is_blank = not plain.strip()
        if is_blank and last_was_blank:
            continue
        _print_markup_or_plain(console, line, rich)
        last_was_blank = is_blank


def get_raw_from_file(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_raw_from_editor() -> str:
    result = edit_entry()
    return result or ""


def get_raw_from_stdin() -> str:
    return sys.stdin.read().strip()


@click.group()
@click.version_option(VERSION, prog_name="tklr", message="%(prog)s version %(version)s")
@click.option(
    "--home",
    help="Override the Tklr workspace directory (equivalent to setting $TKLR_HOME).",
)
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, home, verbose):
    """Tklr CLI – manage your reminders from the command line."""
    if home:
        os.environ["TKLR_HOME"] = (
            home  # Must be set before TklrEnvironment is instantiated
        )

    env = TklrEnvironment()

    if home and not env.home.exists():
        click.confirm(
            f"The Tklr home directory '{env.home}' does not exist. Create it now?",
            default=True,
            abort=True,
        )

    env.ensure(init_config=True, init_db_fn=lambda path: ensure_database(path, env))
    env.load_config()

    ctx.ensure_object(dict)
    ctx.obj["ENV"] = env
    ctx.obj["DB"] = env.db_path
    ctx.obj["VERBOSE"] = verbose


@cli.command()
@click.argument("entry", nargs=-1)
@click.option(
    "--file",
    "-f",
    type=click.Path(exists=True),
    help="Path to file with multiple entries.",
)
@click.option(
    "--batch",
    is_flag=True,
    help="Use editor to create multiple entries separated by blank lines.",
)
@click.pass_context
def add(ctx, entry, file, batch):
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]
    bad_items = []
    dbm = DatabaseManager(db, env)

    def clean_and_split(content: str) -> list[str]:
        """
        Remove comment-like lines (starting with any '#', regardless of spacing)
        and split into entries separated by '...' lines.
        """
        lines = []
        for line in content.splitlines():
            stripped = line.lstrip()  # remove leading whitespace
            if not stripped.startswith("#"):
                lines.append(line)
        cleaned = "\n".join(lines)
        return split_entries(cleaned)

    def split_entries(content: str) -> list[str]:
        """Split raw text into entries using '...' line as separator."""
        return [entry.strip() for entry in content.split("\n...\n") if entry.strip()]

    def get_entries_from_editor() -> list[str]:
        result = edit_entry()
        if not result:
            return []
        return split_entries(result)

    def process_entry(entry_str: str) -> bool:
        msg = None
        try:
            item = Item(env=env, raw=entry_str, final=True)
            if not item.parse_ok or not item.itemtype:
                # pm = "\n".join(item.parse_message)
                # tks = "\n".join(item.relative_tokens)
                msg = f"\n[red]✘ Invalid entry[/red] \nentry: {entry_str}\nparse_message: {item.parse_message}\ntokens: {item.relative_tokens}"
        except Exception as e:
            msg = f"\n[red]✘ Internal error during parsing:[/red]\nentry: {entry_str}\nexception: {e}"

        if msg:
            if verbose:
                print(f"{msg}")
            else:
                bad_items.append(msg)
            return False

        dry_run = False
        if dry_run:
            print(f"[green]would have added:\n {item = }")
        else:
            dbm.add_item(item)
            # print(
            #     f"[green]✔ Added:[/green] {item.subject if hasattr(item, 'subject') else entry_str}"
            # )
        return True

    # Determine the source of entries
    if file:
        entries = clean_and_split(get_raw_from_file(file))
    elif batch:
        entries = clean_and_split(get_raw_from_editor())
    elif entry:
        entries = clean_and_split(" ".join(entry).strip())
    elif not sys.stdin.isatty():
        entries = clean_and_split(get_raw_from_stdin())
    else:
        print("[bold yellow]No entry provided.[/bold yellow]")
        if click.confirm("Create one or more entries in your editor?", default=True):
            entries = clean_and_split(get_entries_from_editor())
        else:
            print("[yellow]✘ Cancelled.[/yellow]")
            sys.exit(1)

    if not entries:
        print("[red]✘ No valid entries to add.[/red]")
        sys.exit(1)

    print(
        f"[blue]➤ Adding {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}[/blue]"
    )
    count = 0
    for e in entries:
        if process_entry(e):
            count += 1

    dbm.populate_dependent_tables()
    print(
        f"[green]✔ Added {count} entr{'y' if count == 1 else 'ies'} successfully.[/green]"
    )
    if bad_items:
        print("\n\n=== Invalid items ===\n")
        for item in bad_items:
            print(item)


@cli.command()
@click.pass_context
def ui(ctx):
    """Launch the Tklr Textual interface."""
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    if verbose:
        print(f"[blue]Launching UI with database:[/blue] {db}")

    controller = Controller(db, env)
    DynamicViewApp(controller).run()


@cli.command()
@click.argument("entry", nargs=-1)
@click.pass_context
def check(ctx, entry):
    """Check whether an entry is valid (parsing only)."""
    env = ctx.obj["ENV"]
    verbose = ctx.obj["VERBOSE"]

    if not entry and not sys.stdin.isatty():
        entry = sys.stdin.read().strip()
    else:
        entry = " ".join(entry).strip()

    if not entry:
        print("[bold red]✘ No entry provided. Use argument or pipe.[/bold red]")
        sys.exit(1)

    try:
        item = Item(env=env, raw=entry)
        if item.parse_ok:
            print("[green]✔ Entry is valid.[/green]")
            if verbose:
                print(f"[blue]Entry:[/blue] {format_tokens(item.relative_tokens)}")
        else:
            print(f"[red]✘ Invalid entry:[/red] {entry!r}")
            print(f"  {item.parse_message}")
            if verbose:
                print(f"[blue]Entry:[/blue] {format_tokens(item.relative_tokens)}")
            sys.exit(1)
    except Exception as e:
        print(f"[red]✘ Unexpected error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.option(
    "--width",
    type=click.IntRange(10, 200),
    default=40,
    help="Maximum line width.",
)
@click.option(
    "--rich",
    is_flag=True,
    help="Use Rich colors/styling (default output is plain).",
)
@click.option(
    "--ids",
    is_flag=True,
    help="Append record ids in parentheses for each reminder row.",
)
@click.pass_context
def agenda(ctx, width, rich, ids):
    """
    Display the current agenda: events for the next 3 days with drafts and notices along with tasks ordered by urgency.

    Examples:
      tklr agenda
      tklr agenda --width 60
      tklr agenda --rich
    """
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    controller = Controller(db, env)
    rows = controller.get_agenda(yield_rows=True)

    if verbose:
        print(f"[blue]Displaying agenda with {len(rows)} items[/blue]")

    # ---- console: plain by default; markup only if --rich ----
    is_tty = sys.stdout.isatty()
    console = Console(
        force_terminal=rich and is_tty,
        no_color=not rich,
        markup=rich,
        highlight=False,
    )

    for i, row in enumerate(rows):
        text = row.get("text", "")
        is_header = row.get("record_id") is None

        from rich.text import Text

        rendered = Text.from_markup(text)
        comparison_text = rendered.plain.strip()

        if not comparison_text:
            continue

        # Add spacing only before the Tasks header
        if is_header and "Tasks" in comparison_text:
            console.print()

        if is_header and "Goals" in comparison_text:
            console.print()

        display_text = rendered if is_header else Text("  ") + rendered

        if len(display_text.plain) > width:
            truncated = display_text.copy()
            truncated.truncate(width, overflow="ellipsis")
        else:
            truncated = display_text

        record_id = row.get("record_id")
        append_id = ids and (record_id is not None) and not is_header

        if rich:
            output_text = truncated
            if append_id:
                suffix_style = "dim"
                output_text = output_text.copy()
                output_text.append(f" ({record_id})", style=suffix_style)
            console.print(output_text)
        else:
            output_plain = truncated.plain
            if append_id:
                output_plain = f"{output_plain} ({record_id})"
            console.print(output_plain, markup=False, highlight=False)


def _parse_local_text_dt(s: str) -> datetime | date:
    """
    Parse DateTimes TEXT ('YYYYMMDD' or 'YYYYMMDDTHHMM') into a
    local-naive datetime or date, matching how DateTimes are stored.
    """
    s = (s or "").strip()
    if not s:
        raise ValueError("empty datetime text")

    if "T" in s:
        # datetime (local naive)
        return datetime.strptime(s, "%Y%m%dT%H%M")
    else:
        # date-only (all-day)
        return datetime.strptime(s, "%Y%m%d").date()


def _format_instance_time(
    start_text: str, end_text: str | None, controller: Controller
) -> str:
    """
    Render a human friendly time range from DateTimes TEXT.
    - date-only: returns '' (treated as all-day)
    - datetime: 'HH:MM' or 'HH:MM-HH:MM'
    """
    start = _parse_local_text_dt(start_text)
    end = _parse_local_text_dt(end_text) if end_text else None
    # get AMPM from config.toml via environment
    AMPM = controller.AMPM

    # date-only => all-day
    if isinstance(start, date) and not isinstance(start, datetime):
        return ""

    return format_time_range(start, end, AMPM)


def _wrap_or_truncate(text: str, width: int) -> str:
    if len(text) <= width:
        return text
    # leave room for an ellipsis
    return text[: max(0, width - 3)] + "…"


def _group_instances_by_date_for_weeks(
    events,
    db_manager: DatabaseManager | None = None,
    controller: Controller | None = None,
) -> Dict[date, List[dict]]:
    """
    events rows from get_events_for_period:
        (dt_id, start_text, end_text, itemtype, subject, record_id, job_id)

    Returns:
        { date -> [ { 'time': time|None,
                      'itemtype': str,
                      'subject': str,
                      'record_id': int,
                      'job_id': int|None,
                      'start_text': str,
                      'end_text': str|None } ] }
    If db_manager is provided, project instances with a job_id will use
    the job's display_subject (matching Controller.get_week_details behavior).
    If controller is provided, event subjects will run through
    apply_anniversary_if_needed to expand {XXX} placeholders.
    """
    grouped: Dict[date, List[dict]] = defaultdict(list)
    job_subject_cache: dict[tuple[int, int], str | None] = {}

    for dt_id, start_text, end_text, itemtype, subject, record_id, job_id in events:
        try:
            parsed = _parse_local_text_dt(start_text)
        except Exception:
            continue  # skip malformed rows

        display_subject = subject or ""
        display_type = itemtype

        if (
            db_manager
            and itemtype == "^"
            and job_id is not None
            and record_id is not None
        ):
            cache_key = (record_id, job_id)
            if cache_key not in job_subject_cache:
                job_subject_cache[cache_key] = db_manager.get_job_display_subject(
                    record_id, job_id
                )
            job_subject = job_subject_cache[cache_key]
            if job_subject:
                display_subject = job_subject

        if isinstance(parsed, datetime):
            d = parsed.date()
            t = parsed.time()
            instance_dt = parsed
        else:
            d = parsed  # a date
            t = None
            instance_dt = datetime.combine(parsed, time.min)

        if (
            controller
            and itemtype == "*"
            and record_id is not None
            and instance_dt is not None
        ):
            display_subject = controller.apply_anniversary_if_needed(
                record_id, display_subject, instance_dt
            )

        grouped[d].append(
            {
                "time": t,
                "itemtype": display_type,
                "subject": display_subject,
                "record_id": record_id,
                "job_id": job_id,
                "start_text": start_text,
                "end_text": end_text,
            }
        )

    # sort each day by time (all-day items first)
    # dict(grouped) as date keys with corresponding sorted list of reminders for that date

    for d in grouped:
        grouped[d].sort(key=lambda r: (r["time"] is not None, r["time"] or time.min))

    return dict(grouped)


@cli.command()
@click.option(
    "--start",
    "start_opt",
    help="Start date (YYYY-MM-DD) or 'today'. Defaults to today.",
)
@click.option(
    "--end",
    "end_opt",
    default="4",
    help="Either an end date (YYYY-MM-DD) or a number of weeks (int). Default: 4.",
)
@click.option(
    "--width",
    type=click.IntRange(10, 200),
    default=40,
    help="Maximum line width (good for small screens).",
)
@click.option(
    "--rich",
    is_flag=True,
    help="Use Rich colors/styling (default output is plain).",
)
@click.option(
    "--ids",
    is_flag=True,
    help="Append record ids in parentheses for each reminder row.",
)
@click.pass_context
def weeks(ctx, start_opt, end_opt, width, rich, ids):
    """
    weeks(start: date = today(), end: date|int = 4, width: int = 40)

    Examples:
      tklr weeks
      tklr weeks --start 2025-11-01 --end 8
      tklr weeks --end 2025-12-31 --width 60
      tklr weeks --rich
    """
    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]

    # dbm = DatabaseManager(db_path, env)
    controller = Controller(db_path, env)
    dbm = controller.db_manager
    verbose = ctx.obj["VERBOSE"]
    if verbose:
        print(f"tklr version: {get_version()}")
        print(f"using home directory: {env.get_home()}")

    # ---- 1) parse start / end into Monday .. Sunday range ----
    if not start_opt or start_opt.lower() == "today":
        start_date = datetime.now().date()
    else:
        start_date = datetime.strptime(start_opt, "%Y-%m-%d").date()

    start_monday = start_date - timedelta(days=start_date.weekday())

    # end_opt can be int weeks or a date
    try:
        weeks_int = int(end_opt)
        end_sunday = start_monday + timedelta(weeks=weeks_int, days=6)
    except (ValueError, TypeError):
        end_date = datetime.strptime(str(end_opt), "%Y-%m-%d").date()
        end_sunday = end_date + timedelta(days=(6 - end_date.weekday()) % 7)

    start_dt = datetime.combine(start_monday, time(0, 0))
    end_dt = datetime.combine(end_sunday, time(23, 59))

    # ---- 2) fetch instances and group by day ----
    events = dbm.get_events_for_period(start_dt, end_dt)
    by_date = _group_instances_by_date_for_weeks(events, dbm, controller)

    # ---- 3) console: plain by default; markup only if --rich ----
    is_tty = sys.stdout.isatty()
    console = Console(
        force_terminal=rich and is_tty,
        no_color=not rich,
        markup=rich,  # still allow [bold] etc when --rich
        highlight=False,  # 👈 disable auto syntax highlighting
    )

    today = datetime.now().date()
    week_start = start_monday

    first_week = True
    while week_start <= end_sunday:
        iso_year, iso_week, _ = week_start.isocalendar()

        if not first_week:
            console.print()
        first_week = False

        # week_label = format_iso_week(datetime.combine(week_start, time(0, 0)))
        #
        # if rich:
        #     console.print(f"[not bold]{week_label}[/not bold]")
        # else:
        #     console.print(week_label)
        week_label = format_iso_week(datetime.combine(week_start, time(0, 0)))

        if rich:
            console.print(f"[bold deep_sky_blue1]{week_label}[/bold deep_sky_blue1]")
        else:
            console.print(week_label)
        # Days within this week
        for i in range(7):
            d = week_start + timedelta(days=i)
            day_events = by_date.get(d, [])
            if not day_events:
                continue  # skip empty days

            # Day header
            flag = " (today)" if d == today else ""
            day_header = f" {d:%a, %b %-d}{flag}"
            console.print(day_header)

            # Day rows, max width
            for row in day_events:
                t = row["time"]
                itemtype = row["itemtype"]
                subject = row["subject"]

                time_str = ""
                if row["start_text"]:
                    time_str = _format_instance_time(
                        row["start_text"], row["end_text"], controller
                    )

                body = (
                    f"{itemtype} {time_str} {subject}"
                    if time_str
                    else f"{itemtype} {subject}"
                )
                record_id = row.get("record_id")
                append_id = ids and (record_id is not None)

                if rich:
                    from rich.text import Text

                    row_text = Text("  ")
                    row_text.append(body, style=TYPE_TO_COLOR.get(itemtype, "white"))
                    display = row_text.copy()
                    if len(display.plain) > width:
                        display.truncate(width, overflow="ellipsis")
                    if append_id:
                        display.append(f" ({record_id})", style="dim")
                    console.print(display)
                else:
                    base = f"  {body}"
                    trimmed = _wrap_or_truncate(base, width)
                    if append_id:
                        trimmed = f"{trimmed} ({record_id})"
                    console.print(trimmed)

            # console.print()  # blank line between days

        week_start += timedelta(weeks=1)


@cli.command()
@click.option(
    "--start",
    "start_opt",
    help="Start date (YYYY-MM-DD) or 'today'. Defaults to today.",
)
@click.option(
    "--end",
    "end_opt",
    default="7",
    help="Either an end date (YYYY-MM-DD) or a number of days (int). Default: 7.",
)
@click.option(
    "--width",
    type=click.IntRange(10, 200),
    default=40,
    help="Maximum line width (good for small screens).",
)
@click.option(
    "--rich",
    is_flag=True,
    help="Use Rich colors/styling (default output is plain).",
)
@click.option(
    "--ids",
    is_flag=True,
    help="Append record ids in parentheses for each reminder row.",
)
@click.pass_context
def days(ctx, start_opt, end_opt, width, rich, ids):
    """
    days(start: date = today(), end: date|int = 7, width: int = 40)

    Display reminders grouped by date without week grouping.

    Examples:
      tklr days
      tklr days --start 2025-11-01 --end 14
      tklr days --end 2025-12-31 --width 60
      tklr days --rich
    """
    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]

    controller = Controller(db_path, env)
    dbm = controller.db_manager
    verbose = ctx.obj["VERBOSE"]
    if verbose:
        print(f"tklr version: {get_version()}")
        print(f"using home directory: {env.get_home()}")

    # ---- 1) parse start / end into date range ----
    if not start_opt or start_opt.lower() == "today":
        start_date = datetime.now().date()
    else:
        start_date = datetime.strptime(start_opt, "%Y-%m-%d").date()

    # end_opt can be int days or a date
    try:
        days_int = int(end_opt)
        end_date = start_date + timedelta(days=days_int - 1)
    except (ValueError, TypeError):
        end_date = datetime.strptime(str(end_opt), "%Y-%m-%d").date()

    start_dt = datetime.combine(start_date, time(0, 0))
    end_dt = datetime.combine(end_date, time(23, 59))

    # ---- 2) fetch instances and group by day ----
    events = dbm.get_events_for_period(start_dt, end_dt)
    by_date = _group_instances_by_date_for_weeks(events, dbm, controller)

    # ---- 3) console: plain by default; markup only if --rich ----
    is_tty = sys.stdout.isatty()
    console = Console(
        force_terminal=rich and is_tty,
        no_color=not rich,
        markup=rich,
        highlight=False,
    )

    today = datetime.now().date()
    current_date = start_date

    first_day = True
    while current_date <= end_date:
        day_events = by_date.get(current_date, [])
        if day_events:  # only show days with events
            if not first_day:
                console.print()
            first_day = False

            # Day header with full date including year
            flag = " (today)" if current_date == today else ""
            day_header = f" {current_date:%a, %b %-d, %Y}{flag}"
            console.print(day_header)

            # Day rows, max width
            for row in day_events:
                itemtype = row["itemtype"]
                subject = row["subject"]

                time_str = ""
                if row["start_text"]:
                    time_str = _format_instance_time(
                        row["start_text"], row["end_text"], controller
                    )

                body = (
                    f"{itemtype} {time_str} {subject}"
                    if time_str
                    else f"{itemtype} {subject}"
                )
                record_id = row.get("record_id")
                append_id = ids and (record_id is not None)

                if rich:
                    from rich.text import Text

                    row_text = Text("  ")
                    row_text.append(body, style=TYPE_TO_COLOR.get(itemtype, "white"))
                    display = row_text.copy()
                    if len(display.plain) > width:
                        display.truncate(width, overflow="ellipsis")
                    if append_id:
                        display.append(f" ({record_id})", style="dim")
                    console.print(display)
                else:
                    base = f"  {body}"
                    trimmed = _wrap_or_truncate(base, width)
                    if append_id:
                        trimmed = f"{trimmed} ({record_id})"
                    console.print(trimmed)

        current_date += timedelta(days=1)


@cli.command()
@click.argument("query_parts", nargs=-1)
@click.option(
    "--limit",
    type=click.IntRange(1, 500),
    help="Maximum number of matches to display.",
)
@click.option(
    "--ids",
    is_flag=True,
    help="Append record ids in parentheses for each matching reminder.",
)
@click.option(
    "--rich",
    is_flag=True,
    help="Use Rich colors/styling (default output is plain).",
)
@click.pass_context
def query(ctx, query_parts, limit, ids, rich):
    """Run an advanced query and list matching reminders."""
    query_text = " ".join(query_parts).strip()
    is_tty = sys.stdout.isatty()
    console = Console(
        force_terminal=rich and is_tty,
        no_color=not rich,
        markup=rich,
        highlight=False,
    )
    if not query_text:
        console.print("Enter a query string.")
        ctx.exit(1)

    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]
    controller = Controller(db_path, env)

    try:
        response = controller.run_query(query_text)
    except QueryError as exc:
        if rich:
            console.print(f"[red]Query error:[/red] {exc}")
        else:
            console.print(f"Query error: {exc}")
        ctx.exit(1)

    if response.info_id is not None:
        record_id = response.info_id
        try:
            title, lines, _ = controller.get_details_for_record(record_id)
        except Exception:
            console.print(f"No record found with id {record_id}.")
            ctx.exit(1)
        _print_detail_lines(console, lines, rich)
        return

    matches = response.matches
    total = len(matches)
    if total == 0:
        console.print("No results.")
        return

    if limit is not None and limit < total:
        display_matches = matches[:limit]
    else:
        display_matches = matches

    for match in display_matches:
        subject = match.subject or "(untitled)"
        if rich:
            from rich.text import Text

            color = TYPE_TO_COLOR.get(match.itemtype, "white")
            line = Text()
            line.append(f"{match.itemtype} {subject}", style=color)
            if ids:
                line.append(f" ({match.record_id})", style="dim")
            console.print(line)
        else:
            line = f"{match.itemtype} {subject}"
            if ids:
                line = f"{line} ({match.record_id})"
            console.print(line)

    if limit is not None and limit < total:
        console.print(f"Showing first {limit} of {total} matches.")
    else:
        suffix = "" if total == 1 else "es"
        console.print(f"{total} match{suffix}.")


@cli.command()
@click.argument("finish_parts", nargs=-1)
@click.option(
    "--yes",
    "-y",
    is_flag=True,
    help="Apply finish without prompting for confirmation.",
)
@click.pass_context
def finish(ctx, finish_parts, yes):
    """
    Mark a reminder finished, providing the id and, optionally, the completion datetime.
    """
    if not finish_parts:
        print("[red]Enter the record id to finish.[/red]")
        ctx.exit(1)

    id_text = finish_parts[0]
    try:
        record_id = int(id_text)
    except ValueError:
        print(f"[red]Invalid record id:[/red] {id_text!r}")
        ctx.exit(1)

    when_text = " ".join(finish_parts[1:]).strip()
    if when_text:
        try:
            finish_dt = dt_parser.parse(when_text)
        except (ValueError, dt_parser.ParserError) as exc:
            print(f"[red]Could not parse finish datetime:[/red] {exc}")
            ctx.exit(1)
    else:
        finish_dt = datetime.now()

    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]
    controller = Controller(db_path, env)

    record = controller.db_manager.get_record_as_dictionary(record_id)
    if not record:
        print(f"[red]No record found with id {record_id}.[/red]")
        ctx.exit(1)

    subject = record.get("subject") or "(untitled)"
    finish_label = controller.fmt_user(finish_dt)

    if not yes:
        prompt = f"Finish {record_id}: {subject!r}\nat {finish_label}?"
        if not click.confirm(prompt, default=False):
            print("[yellow]Finish cancelled.[/yellow]")
            return

    try:
        changed = controller.finish_task(record_id, job_id=None, when=finish_dt)
    except Exception as exc:
        print(f"[red]Finish failed:[/red] {exc}")
        ctx.exit(1)

    if not changed:
        print("[yellow]No changes made; task may already be finished.[/yellow]")
        return

    controller.db_manager.populate_dependent_tables()
    print(f"[green]✔ Finished[/green] {subject!r} ({record_id})\nat {finish_label}")


@cli.command()
@click.argument("regex_parts", nargs=-1)
@click.pass_context
def find(ctx, regex_parts):
    """
    Search reminders whose subject or @d description matches a case-insensitive regex.

    Examples:
        tklr find waldo
        tklr find '(?i)project\\d+'
    """
    pattern = " ".join(regex_parts).strip()
    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]
    controller = Controller(db_path, env)

    matches = controller.db_manager.find_records(pattern)
    if not matches:
        if pattern:
            print(f"No reminders matched {pattern!r}.")
        else:
            print("No reminders found.")
        return

    for record_id, subject, _description, itemtype, _last_ts, _next_ts in matches:
        subj = subject or "(untitled)"
        print(f"{itemtype} {subj} (id {record_id})")

    suffix = "" if len(matches) == 1 else "es"
    print(f"{len(matches)} match{suffix}.")


@cli.command()
@click.argument("record_id", type=int)
@click.option(
    "--rich",
    is_flag=True,
    help="Use Rich colors/styling (default output is plain).",
)
@click.pass_context
def details(ctx, record_id, rich):
    """
    Display the details for a reminder with the provided id.
    """
    env = ctx.obj["ENV"]
    db_path = ctx.obj["DB"]
    controller = Controller(db_path, env)

    try:
        title, lines, _ = controller.get_details_for_record(record_id)
    except Exception:
        print(f"[red]No record found with id {record_id}.[/red]")
        ctx.exit(1)

    is_tty = sys.stdout.isatty()
    console = Console(
        force_terminal=rich and is_tty,
        no_color=not rich,
        markup=rich,
        highlight=False,
    )

    _print_detail_lines(console, lines, rich)


@cli.command()
@click.argument("etm_dir", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--outfile",
    type=click.Path(dir_okay=False),
    help="Defaults to [--home]/etm.txt",
)
@click.option(
    "--secret",
    help="Secret from etm cfg.yaml used to decode @m values. Absent a valid 'secret', @m values will be left encoded. (default: None)",
)
@click.option(
    "--record-ids",
    is_flag=True,
    help="Append @# tags with the original etm record ids. (default: False)",
)
@click.option(
    "--include-archive",
    is_flag=True,
    help="Include archived etm entries. (default: False)",
)
@click.option(
    "--types",
    type=click.Choice(MIGRATION_ITEM_TYPES),
    multiple=True,
    help="Restrict migration to specific etm item types (default: all).",
)
@click.pass_context
def migrate(
    ctx,
    etm_dir,
    outfile,
    secret,
    record_ids,
    include_archive,
    types,
):
    """
    Convert ETM reminders into a Tklr batch-entry file for the current home.

    Migrated reminders will be extracted from the ``etm.json`` file in ETM_DIR .

    Example:

      tklr --home ~/.config/tklr migrate ~/etm
    """

    env = ctx.obj["ENV"]
    etm_dir_path = Path(etm_dir)
    outfile_path = Path(outfile) if outfile else env.home / "etm.txt"
    allowed = set(types) if types else None

    try:
        count = migrate_etm_directory(
            etm_dir_path,
            outfile_path,
            secret=secret,
            include_archive=include_archive,
            include_record_ids=record_ids,
            allowed_item_types=allowed,
        )
    except FileNotFoundError as exc:
        raise click.UsageError(str(exc)) from exc

    noun = "record" if count == 1 else "records"
    click.echo(f"Migrated {count} {noun} to {outfile_path}")
