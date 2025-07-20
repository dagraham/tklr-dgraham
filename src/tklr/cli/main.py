import sys
import click
import importlib.metadata
# import shutil

from rich import print
from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager
from tklr.view import DynamicViewApp
from tklr.tklr_env import TklrEnvironment

env = TklrEnvironment()
# urgency = env.config.urgency.model_dump()
urgency = env.config.urgency
print(f"{urgency = }\n{urgency.due.max = }")
# urgency = env.config.urgency
# print(f"{urgency = }\n{urgency.active_value = }\n{urgency.priority.high = }")
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
    """Add an item via command-line, pipe, or external editor."""

    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    def edit_entry(initial: str, reason: str = "") -> str | None:
        header = ""
        if reason:
            header = f"# Fix the entry below or return unchanged to cancel.\n# ERROR: {reason}\n# Lines starting with # will be ignored.\n"
        result = click.edit(header + initial.strip(), extension=".tklr")
        if result is None:
            return None
        lines = [
            line for line in result.splitlines() if not line.strip().startswith("#")
        ]
        return "\n".join(lines).strip() or None

    # 1. Determine initial entry
    if entry:
        entry_str = " ".join(entry).strip()
        interactive = False
    elif not sys.stdin.isatty():
        entry_str = sys.stdin.read().strip()
        interactive = False
    else:
        print("[bold yellow]No entry provided.[/]")
        if click.confirm("Create the entry in your editor?", default=True):
            entry_str = edit_entry("") or ""
            interactive = True
        else:
            print("[yellow]✘ Cancelled.[/]")
            sys.exit(1)

    if not entry_str:
        print("[red]✘ Empty entry; nothing to add.[/]")
        sys.exit(1)

    was_edited = not (entry or not sys.stdin.isatty())

    # 2. Parse-check loop
    while True:
        try:
            item = Item(entry_str)
        except Exception as e:
            print(f"exception: {e = }")
            print(f"[red]✘ Internal error during parsing:[/] {e}")
            sys.exit(1)

        if not item.parse_ok:
            print(f"[red]✘ Invalid entry:[/] {entry_str!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(
                    f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}"
                )

            if interactive or sys.stdout.isatty():
                edited = edit_entry(entry_str, reason=item.parse_message)
                if not edited:
                    print("[yellow]✘ Cancelled or empty after editing.[/]")
                    sys.exit(1)
                entry_str = edited
                was_edited = True
                continue
            else:
                print("[red]✘ Entry invalid. Exiting.[/]")
                sys.exit(1)

        # ✔ Entry is valid
        print("[green]✔ Entry is valid.[/]")
        if verbose:
            print(f"{item = }")
            # print(f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}")

        # Only confirm if interactive and wasn't already edited
        if interactive and not was_edited:
            if not click.confirm("Add this item to the database?", default=True):
                print("[yellow]✔ Entry was valid but not added.[/]")
                sys.exit(0)

        dbm = DatabaseManager(db, env)
        dbm.add_item(item)
        dbm.populate_dependent_tables()
        print("[green]✔ Item added to database.[/]")
        sys.exit(0)


@cli.command()
@click.pass_context
def ui(ctx):
    """Launch the Tklr Textual interface."""
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]
    controller = Controller(db, env)

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
