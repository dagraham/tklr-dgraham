import sys
import os
import click
from pathlib import Path
# from rich import print

from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager, UrgencyComputer
from tklr.view import DynamicViewApp
from tklr.tklr_env import TklrEnvironment
from tklr.view_agenda import run_agenda_view
from tklr.common import get_version
from tklr.shared import log_msg
from tklr.shared import print_msg as print

VERSION = get_version()


def ensure_database(db_path: str, env: TklrEnvironment):
    if not Path(db_path).exists():
        print(f"[yellow]⚠️ Database not found. Creating new database at {db_path}[/]")
        dbm = DatabaseManager(db_path, env)
        dbm.setup_database()


def format_tokens(tokens, width=80):
    return " ".join([f"{t['token'].strip()}" for t in tokens])


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
    env.ensure(init_db_fn=lambda path: ensure_database(path, env))
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
    dbm = DatabaseManager(db, env)

    # def clean_and_split(content: str) -> list[str]:
    #     """Remove comment lines and split into entries separated by blank lines."""
    #     lines = [
    #         line for line in content.splitlines() if not line.strip().startswith("#")
    #     ]
    #     return [
    #         entry.strip() for entry in "\n".join(lines).split("\n\n") if entry.strip()
    #     ]

    def clean_and_split(content: str) -> list[str]:
        """Remove comment lines and split into entries separated by '...' markers."""
        lines = [
            line for line in content.splitlines() if not line.strip().startswith("#")
        ]
        cleaned = "\n".join(lines)
        return split_entries(cleaned)

    def edit_entry(initial: str = "") -> str | None:
        result = click.edit(initial, extension=".tklr")
        if result is None:
            return None
        entries = clean_and_split(result)
        return "\n\n".join(entries) if entries else None

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
        try:
            item = Item(raw=entry_str, final=True)
        except Exception as e:
            print(f"[red]✘ Internal error during parsing:[/] {e}; {entry_str = }")
            return False

        if not item.parse_ok or not item.itemtype:
            print(f"[red]✘ Invalid entry:[/] {entry_str!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(f"[blue]Parsed tokens:[/] {format_tokens(item.relative_tokens)}")
            return False

        dry_run = False
        if dry_run:
            print(f"[green]would have added:\n {item = }")
        else:
            dbm.add_item(item)
            print(
                f"[green]✔ Added:[/] {item.subject if hasattr(item, 'subject') else entry_str}"
            )
        return True

    # Determine the source of entries
    if file:
        entries = get_entries_from_file(file)
    elif batch:
        entries = get_entries_from_editor()
    elif entry:
        entries = [" ".join(entry).strip()]
    elif not sys.stdin.isatty():
        entries = get_entries_from_stdin()
    else:
        print("[bold yellow]No entry provided.[/]")
        if click.confirm("Create one or more entries in your editor?", default=True):
            entries = get_entries_from_editor()
        else:
            print("[yellow]✘ Cancelled.[/]")
            sys.exit(1)

    if not entries:
        print("[red]✘ No valid entries to add.[/]")
        sys.exit(1)

    print(f"[blue]➤ Adding {len(entries)} entr{'y' if len(entries) == 1 else 'ies'}[/]")
    count = 0
    for e in entries:
        if process_entry(e):
            count += 1

    dbm.populate_dependent_tables()
    print(f"[green]✔ Added {count} entr{'y' if count == 1 else 'ies'} successfully.[/]")


@cli.command()
@click.pass_context
def ui(ctx):
    """Launch the Tklr Textual interface."""
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    if verbose:
        print(f"[blue]Launching UI with database:[/] {db}")
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
        print("[bold red]✘ No entry provided. Use argument or pipe.[/]")
        sys.exit(1)

    try:
        item = Item(entry)
        if item.parse_ok:
            print("[green]✔ Entry is valid.[/]")
            if verbose:
                print(f"[blue]Entry:[/] {format_tokens(item.relative_tokens)}")
        else:
            print(f"[red]✘ Invalid entry:[/] {entry!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(f"[blue]Entry:[/] {format_tokens(item.relative_tokens)}")
            sys.exit(1)
    except Exception as e:
        print(f"[red]✘ Unexpected error:[/] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def agenda(ctx):
    """Launch the Tklr agenda split-screen view."""
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    if verbose:
        print(f"[blue]Launching agenda view with database:[/] {db}")

    controller = Controller(db, env)
    run_agenda_view(controller)
