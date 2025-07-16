#!/usr/bin/env python3
import sys
import argparse
from rich import print
from tklr.item import Item
from tklr.model import DatabaseManager


def add_item(
    entry: str, db_path: str, dry_run: bool = False, verbose: bool = False
) -> None:
    if verbose:
        print(f"[blue]Input:[/] {entry!r}")
    try:
        item = Item(entry)
        if verbose:
            print(f"[blue]Parsed Item:[/] {item}")
        if dry_run:
            print("[yellow]Dry run:[/] Item was parsed but not added to the database.")
        else:
            dbm = DatabaseManager(db_path)
            dbm.add_item(item)
            dbm.populate_dependent_tables()
            print("[green]✔ Item added successfully.[/]")
    except Exception as e:
        print(f"[red]✘ Error:[/] {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Add a Tklr item via CLI.")
    parser.add_argument(
        "entry",
        nargs="?",
        help="Item entry string (use quotes). If not provided, read from stdin.",
    )
    parser.add_argument(
        "--db",
        default="./example/tklr.db",
        help="Path to Tklr database (default: ./example/tklr.db)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse and validate the item without writing to the database.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Print additional debug information.",
    )

    args = parser.parse_args()

    if args.entry:
        add_item(args.entry, args.db, args.dry_run, args.verbose)
    elif not sys.stdin.isatty():
        # Read piped input
        piped = sys.stdin.read().strip()
        if piped:
            add_item(piped, args.db, args.dry_run, args.verbose)
        else:
            print("[red]✘ No input provided from pipe.[/]")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
