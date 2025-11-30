import sys
import os
import click
from pathlib import Path
from rich import print
from typing import Dict, List, Tuple, Optional

from collections import defaultdict

from rich.console import Console
# from rich.table import Table

from tklr.item import Item
from tklr.controller import Controller, format_iso_week
from tklr.model import DatabaseManager
from tklr.view import DynamicViewApp
from tklr.tklr_env import TklrEnvironment

# from tklr.view_agenda import run_agenda_view
from tklr.versioning import get_version
from tklr.shared import format_time_range

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
    env.ensure(init_config=True, init_db_fn=lambda path: ensure_database(path, env))
    config = env.load_config()

    ctx.ensure_object(dict)
    ctx.obj["ENV"] = env
    ctx.obj["DB"] = env.db_path
    ctx.obj["CONFIG"] = config
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

    def get_entries_from_file(path: str) -> list[str]:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
        return split_entries(content)

    def get_entries_from_stdin() -> list[str]:
        data = sys.stdin.read().strip()
        return split_entries(data)

    def process_entry(entry_str: str) -> bool:
        exception = False
        msg = None
        try:
            item = Item(raw=entry_str, final=True)
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
    verbose = ctx.obj["VERBOSE"]

    if not entry and not sys.stdin.isatty():
        entry = sys.stdin.read().strip()
    else:
        entry = " ".join(entry).strip()

    if not entry:
        print("[bold red]✘ No entry provided. Use argument or pipe.[/bold red]")
        sys.exit(1)

    try:
        item = Item(entry)
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
@click.pass_context
def agenda(ctx):
    """Display the current agenda."""
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    if verbose:
        print(f"[blue]Launching agenda view with database:[/blue] {db}")

    controller = Controller(db, env)
    run_agenda_view(controller)


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


def _group_instances_by_date_for_weeks(events) -> Dict[date, List[dict]]:
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
    """
    grouped: Dict[date, List[dict]] = defaultdict(list)

    for dt_id, start_text, end_text, itemtype, subject, record_id, job_id in events:
        try:
            parsed = _parse_local_text_dt(start_text)
        except Exception:
            continue  # skip malformed rows

        if isinstance(parsed, datetime):
            d = parsed.date()
            t = parsed.time()
        else:
            d = parsed  # a date
            t = None

        grouped[d].append(
            {
                "time": t,
                "itemtype": itemtype,
                "subject": subject or "",
                "record_id": record_id,
                "job_id": job_id,
                "start_text": start_text,
                "end_text": end_text,
            }
        )

    # sort each day by time (all-day items first)
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
@click.pass_context
def weeks(ctx, start_opt, end_opt, width, rich):
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
    by_date = _group_instances_by_date_for_weeks(events)

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
        week_end = week_start + timedelta(days=6)
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

                if time_str:
                    base = f"  {itemtype} {time_str} {subject}"
                else:
                    base = f"  {itemtype} {subject}"

                console.print(_wrap_or_truncate(base, width))

            # console.print()  # blank line between days

        week_start += timedelta(weeks=1)
