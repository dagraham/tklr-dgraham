import sys
import click
import importlib.metadata
import shutil

from rich import print
from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager
from tklr.view import DynamicViewApp

# width = shutil.get_terminal_size()[0] - 2
# width = 30


def format_tokens(tokens):
    return " ".join([f"{t['token'].strip()}" for t in tokens])


@click.group()
@click.version_option(
    importlib.metadata.version("tklr"),
    prog_name="tklr",
    message="%(prog)s version %(version)s",
)
@click.option("--db", default="./example/tklr.db", help="Path to Tklr database")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx, db, verbose):
    """Tklr CLI – manage your reminders from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["DB"] = db
    ctx.obj["VERBOSE"] = verbose


@cli.command()
@click.argument("entry", nargs=-1)
@click.pass_context
def add(ctx, entry):
    """Add an item via command-line, pipe, or interactively."""
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    # 1. Determine input source
    if entry:
        entry_str = " ".join(entry).strip()
    elif not sys.stdin.isatty():
        entry_str = sys.stdin.read().strip()
    else:
        print("[bold yellow]No entry given.[/] [dim]Let's add one interactively.")
        print("[dim]Begin your entry with *, -, ~, or % for the item type")
        print("[dim]and when complete, press Enter to submit:")
        try:
            entry_str = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[red]✘ Input cancelled.[/]")
            sys.exit(1)

    if not entry_str:
        print("[bold red]✘ No entry provided. Use argument, pipe, or interactively.[/]")
        sys.exit(1)

    # 2. Parse and check
    try:
        item = Item(entry_str)

        if not item.parse_ok:
            print(f"[red]✘ Invalid entry:[/] {entry_str!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens)}")
            sys.exit(1)

        print(f"[green]✔ Entry is valid.[/]")
        if verbose or sys.stdin.isatty():
            print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens)}")

        # 3. Ask user to confirm before adding (only if interactive)
        if sys.stdin.isatty():
            answer = input("Add this item to the database? [Y/n] ").strip().lower()
            if answer in ("n", "no"):
                print("[yellow]✔ Entry was valid but not added.[/]")
                sys.exit(0)

        # 4. Add to DB
        dbm = DatabaseManager(db)
        dbm.add_item(item)
        dbm.populate_dependent_tables()
        print("[green]✔ Item added to database.[/]")

    except Exception as e:
        print(f"[red]✘ Unexpected error:[/] {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def ui(ctx):
    """Launch the Tklr Textual interface."""
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]
    controller = Controller(db)

    if verbose:
        print(f"[blue]Launching UI with database:[/] {db}")
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
                print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens, width)}")
        else:
            print(f"[red]✘ Invalid entry:[/] {entry!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens, width)}")
            sys.exit(1)

    except Exception as e:
        print(f"[red]✘ Unexpected error:[/] {e}")
        sys.exit(1)
