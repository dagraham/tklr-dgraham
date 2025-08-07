import sys
import os
import click
from pathlib import Path
from rich import print

from tklr.item import Item
from tklr.controller import Controller
from tklr.model import DatabaseManager, UrgencyComputer
from tklr.view import DynamicViewApp
from tklr.tklr_env import TklrEnvironment
from tklr.view_agenda import run_agenda_view
from tklr.common import get_version

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
@click.pass_context
def add(ctx, entry):
    env = ctx.obj["ENV"]
    db = ctx.obj["DB"]
    verbose = ctx.obj["VERBOSE"]

    def edit_entry(initial: str) -> str | None:
        result = click.edit(initial, extension=".tklr")
        if result is None:
            return None
        lines = [
            line for line in result.splitlines() if not line.strip().startswith("#")
        ]
        return "\n".join(lines).strip() or None

    if entry:
        entry_str = " ".join(entry).strip()
    elif not sys.stdin.isatty():
        entry_str = sys.stdin.read().strip()
    else:
        print("[bold yellow]No entry provided.[/]")
        if click.confirm("Create the entry in your editor?", default=True):
            entry_str = edit_entry("") or ""
        else:
            print("[yellow]✘ Cancelled.[/]")
            sys.exit(1)

    if not entry_str:
        print("[red]✘ Empty entry; nothing to add.[/]")
        sys.exit(1)

    while True:
        try:
            item = Item(entry_str)
        except Exception as e:
            print(f"[red]✘ Internal error during parsing:[/] {e}")
            sys.exit(1)

        if not item.parse_ok:
            print(f"[red]✘ Invalid entry:[/] {entry_str!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(
                    f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}"
                )

            if sys.stdout.isatty() and click.confirm(
                "Edit this entry in your editor?", default=True
            ):
                entry_str = edit_entry(entry_str) or ""
                if not entry_str:
                    print("[yellow]✘ Cancelled or empty after editing.[/]")
                    sys.exit(1)
                continue

            print("[red]✘ Entry invalid. Exiting.[/]")
            sys.exit(1)

        print("[green]✔ Entry is valid.[/]")
        if verbose:
            print(f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}")

        dbm = DatabaseManager(db, env)
        dbm.add_item(item)
        dbm.populate_dependent_tables()
        print("[green]✔ Item added to database.[/]")
        sys.exit(0)


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
                print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens)}")
        else:
            print(f"[red]✘ Invalid entry:[/] {entry!r}")
            print(f"  [yellow]{item.parse_message}[/]")
            if verbose:
                print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens)}")
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


# ------------
# import sys
# import os
# import click
# import importlib.metadata
# # import shutil
#
# from rich import print
# from tklr.item import Item
# from tklr.controller import Controller
# from tklr.model import DatabaseManager
# from tklr.view import DynamicViewApp
# from tklr.tklr_env import TklrEnvironment
# from pathlib import Path
# from tklr.view_agenda import run_agenda_view
# from tklr.common import get_version
#
# # env = TklrEnvironment()
# # DEFAULT_DB_PATH = env.db_path
# # urgency = env.config.urgency
# # print(f"{urgency = }")
# # print(f"{urgency.priority = }")
#
# VERSION = get_version()
#
#
# def format_tokens(tokens):
#     return " ".join([f"{t['token'].strip()}" for t in tokens])
#
#
# def ensure_database(db_path: str, env: TklrEnvironment):
#     from tklr.model import DatabaseManager
#
#     if not Path(db_path).exists():
#         print(f"[yellow]⚠️ Database not found. Creating new database at {db_path}[/]")
#         dbm = DatabaseManager(db_path, env)
#         dbm.setup_database()
#
#
# @click.group()
# @click.version_option(
#     # importlib.metadata.version("tklr"),
#     VERSION,
#     prog_name="tklr",
#     message="%(prog)s version %(version)s",
# )
# @click.option(
#     "--home",
#     help="Override the Tklr workspace directory (equivalent to setting $TKLR_HOME).",
# )
# @click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
# @click.pass_context
# def cli(ctx, home, verbose):
#     """Tklr CLI – manage your reminders from the command line."""
#     if home:
#         os.environ["TKLR_HOME"] = home  # must be set before using TklrEnvironment
#
#     env = TklrEnvironment()
#     env.ensure(init_db_fn=lambda db_path: ensure_database(db_path, env))
#
#     config = env.load_config()
#
#     ctx.ensure_object(dict)
#     ctx.obj["ENV"] = env
#     ctx.obj["DB"] = env.db_path
#     ctx.obj["VERBOSE"] = verbose
#     ctx.obj["CONFIG"] = config
#     ctx.obj["HOME"] = str(env.home)
#     print(f"{home =  }, {env.home = }, {env.db_path = }, {config = }")
#
#
# @cli.command()
# @click.argument("entry", nargs=-1)
# @click.pass_context
# def add(ctx, entry):
#     db = ctx.obj["DB"]
#     verbose = ctx.obj["VERBOSE"]
#
#     def edit_entry(initial: str) -> str | None:
#         result = click.edit(initial, extension=".tklr")
#         if result is None:
#             return None
#         lines = [
#             line for line in result.splitlines() if not line.strip().startswith("#")
#         ]
#         return "\n".join(lines).strip() or None
#
#     # 1. Determine initial entry
#     if entry:
#         entry_str = " ".join(entry).strip()
#     elif not sys.stdin.isatty():
#         entry_str = sys.stdin.read().strip()
#     else:
#         print("[bold yellow]No entry provided.[/]")
#         if click.confirm("Create the entry in your editor?", default=True):
#             entry_str = edit_entry("") or ""
#         else:
#             print("[yellow]✘ Cancelled.[/]")
#             sys.exit(1)
#
#     if not entry_str:
#         print("[red]✘ Empty entry; nothing to add.[/]")
#         sys.exit(1)
#
#     # 2. Parse-check loop
#     while True:
#         try:
#             item = Item(entry_str)
#         except Exception as e:
#             print(f"[red]✘ Internal error during parsing:[/] {e}")
#             sys.exit(1)
#
#         if not item.parse_ok:
#             print(f"[red]✘ Invalid entry:[/] {entry_str!r}")
#             print(f"  [yellow]{item.parse_message}[/]")
#             if verbose:
#                 print(
#                     f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}"
#                 )
#
#             if sys.stdout.isatty():
#                 if click.confirm("Edit this entry in your editor?", default=True):
#                     entry_str = edit_entry(entry_str) or ""
#                     if not entry_str:
#                         print("[yellow]✘ Cancelled or empty after editing.[/]")
#                         sys.exit(1)
#                     continue
#             print("[red]✘ Entry invalid. Exiting.[/]")
#             sys.exit(1)
#
#         print("[green]✔ Entry is valid.[/]")
#         if verbose:
#             print(f"[blue]Parsed tokens:[/] {format_tokens(item.structured_tokens)}")
#
#         dbm = DatabaseManager(db, env)
#         dbm.add_item(item)
#         dbm.populate_dependent_tables()
#         print("[green]✔ Item added to database.[/]")
#         sys.exit(0)
#
#
# @cli.command()
# @click.pass_context
# def ui(ctx):
#     """Launch the Tklr Textual interface."""
#     db = ctx.obj["DB"]
#     verbose = ctx.obj["VERBOSE"]
#
#     env = ctx.obj["ENV"]
#     home = ctx.obj["HOME"]
#     controller = Controller(db, env)
#
#     if verbose:
#         print(f"[blue]Launching UI with tklr home:[/] {home}")
#     DynamicViewApp(controller).run()
#
#
# @cli.command()
# @click.argument("entry", nargs=-1)
# @click.pass_context
# def check(ctx, entry):
#     """Check whether an entry is valid (parsing only)."""
#     verbose = ctx.obj["VERBOSE"]
#
#     if not entry and not sys.stdin.isatty():
#         entry = sys.stdin.read().strip()
#     else:
#         entry = " ".join(entry).strip()
#
#     if not entry:
#         print("[bold red]✘ No entry provided. Use argument or pipe.[/]")
#         sys.exit(1)
#
#     try:
#         item = Item(entry)
#         if item.parse_ok:
#             print("[green]✔ Entry is valid.[/]")
#             if verbose:
#                 print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens, width)}")
#         else:
#             print(f"[red]✘ Invalid entry:[/] {entry!r}")
#             print(f"  [yellow]{item.parse_message}[/]")
#             if verbose:
#                 print(f"[blue]Entry:[/] {format_tokens(item.structured_tokens, width)}")
#             sys.exit(1)
#
#     except Exception as e:
#         print(f"[red]✘ Unexpected error:[/] {e}")
#         sys.exit(1)
#
#
# @cli.command()
# @click.pass_context
# def agenda(ctx):
#     """Launch the Tklr agenda split-screen view."""
#     env = ctx.obj["ENV"]
#     db = ctx.obj["DB"]
#     verbose = ctx.obj["VERBOSE"]
#     home = ctx.obj["HOME"]
#     controller = Controller(db, env)
#
#     if verbose:
#         print(f"[blue]Launching agenda view with tklr home:[/] {home}")
#
#     run_agenda_view(controller)
