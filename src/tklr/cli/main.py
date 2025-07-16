import sys
import click
import importlib.metadata

from rich import print
from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager
from tklr.view import DynamicViewApp


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
@click.argument("entry", required=False)
@click.option("--dry-run", is_flag=True, help="Parse but do not add to the database")
@click.pass_context
def add(ctx, entry, dry_run):
    """Add an item via command-line or piped input."""
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    if not entry and not sys.stdin.isatty():
        entry = sys.stdin.read().strip()

    if not entry:
        print("[red]✘ No entry provided. Use argument or pipe.[/]")
        sys.exit(1)

    try:
        if verbose:
            print(f"[blue]Input:[/] {entry!r}")
        item = Item(entry)
        if verbose:
            print(f"[blue]Parsed Item:[/] {item}")
        if dry_run:
            print("[yellow]Dry run:[/] Item parsed but not added.")
        else:
            dbm = DatabaseManager(db)
            dbm.add_item(item)
            dbm.populate_dependent_tables()
            print("[green]✔ Item added to database.[/]")
    except Exception as e:
        print(f"[red]✘ Error:[/] {e}")
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
