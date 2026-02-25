#!/usr/bin/env python3
"""
Remove exact duplicate rows from the Completions table.

Duplicates are rows with the same:
    - record_id
    - completed
    - due

By default this script performs a dry run and prints what would be removed.
Use --apply to execute the deletion.
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class DuplicateGroup:
    record_id: int
    completed: str
    due: str | None
    count: int
    keep_id: int

    @property
    def remove_count(self) -> int:
        return max(0, self.count - 1)


@dataclass(frozen=True)
class NullDueGroup:
    record_id: int
    completed: str
    null_rows: int
    nonnull_rows: int
    sample_keep_id: int

    @property
    def remove_count_after_exact(self) -> int:
        # Exact dedupe runs first and leaves at most one NULL-due row in the group.
        return 1


def _resolve_default_home() -> Path:
    cwd = Path.cwd()
    if (cwd / "config.toml").exists() and (cwd / "tklr.db").exists():
        return cwd

    env_home = os.getenv("TKLR_HOME")
    if env_home:
        return Path(env_home).expanduser()

    xdg_home = os.getenv("XDG_CONFIG_HOME")
    if xdg_home:
        return Path(xdg_home).expanduser() / "tklr"

    return Path.home() / ".config" / "tklr"


def _resolve_db_path(db_arg: str | None) -> Path:
    if db_arg:
        return Path(db_arg).expanduser().resolve()
    return (_resolve_default_home() / "tklr.db").resolve()


def _fetch_duplicate_groups(conn: sqlite3.Connection, keep: str) -> list[DuplicateGroup]:
    agg = conn.execute(
        """
        SELECT
            record_id,
            completed,
            due,
            COUNT(*) AS cnt,
            MIN(id) AS min_id,
            MAX(id) AS max_id
        FROM Completions
        GROUP BY record_id, completed, due
        HAVING COUNT(*) > 1
        ORDER BY cnt DESC, record_id ASC, completed ASC
        """
    ).fetchall()

    groups: list[DuplicateGroup] = []
    for record_id, completed, due, cnt, min_id, max_id in agg:
        keep_id = min_id if keep == "oldest" else max_id
        groups.append(
            DuplicateGroup(
                record_id=record_id,
                completed=completed,
                due=due,
                count=cnt,
                keep_id=keep_id,
            )
        )
    return groups


def _build_delete_sql(keep: str) -> str:
    comparator = ">" if keep == "oldest" else "<"
    return f"""
        DELETE FROM Completions
        WHERE id IN (
            SELECT c1.id
            FROM Completions c1
            JOIN Completions c2
              ON c1.record_id = c2.record_id
             AND c1.completed = c2.completed
             AND (
                    (c1.due = c2.due)
                 OR (c1.due IS NULL AND c2.due IS NULL)
             )
             AND c1.id {comparator} c2.id
        )
    """


def _fetch_null_due_groups(conn: sqlite3.Connection) -> list[NullDueGroup]:
    rows = conn.execute(
        """
        SELECT
            record_id,
            completed,
            SUM(CASE WHEN due IS NULL THEN 1 ELSE 0 END) AS null_cnt,
            SUM(CASE WHEN due IS NOT NULL THEN 1 ELSE 0 END) AS nonnull_cnt,
            MIN(CASE WHEN due IS NOT NULL THEN id END) AS sample_keep_id
        FROM Completions
        GROUP BY record_id, completed
        HAVING
            SUM(CASE WHEN due IS NULL THEN 1 ELSE 0 END) > 0
            AND
            SUM(CASE WHEN due IS NOT NULL THEN 1 ELSE 0 END) > 0
        ORDER BY null_cnt DESC, record_id ASC, completed ASC
        """
    ).fetchall()

    return [
        NullDueGroup(
            record_id=record_id,
            completed=completed,
            null_rows=null_cnt,
            nonnull_rows=nonnull_cnt,
            sample_keep_id=sample_keep_id,
        )
        for (record_id, completed, null_cnt, nonnull_cnt, sample_keep_id) in rows
    ]


def _build_delete_null_due_sql() -> str:
    return """
        DELETE FROM Completions
        WHERE due IS NULL
          AND EXISTS (
                SELECT 1
                FROM Completions c2
                WHERE c2.record_id = Completions.record_id
                  AND c2.completed = Completions.completed
                  AND c2.due IS NOT NULL
          )
    """


def _print_groups(groups: Iterable[DuplicateGroup], *, max_rows: int = 20) -> None:
    shown = 0
    for grp in groups:
        if shown >= max_rows:
            break
        due_text = grp.due if grp.due is not None else "NULL"
        print(
            f"record_id={grp.record_id} completed={grp.completed} due={due_text} "
            f"rows={grp.count} keep_id={grp.keep_id} remove={grp.remove_count}"
        )
        shown += 1


def _print_null_due_groups(groups: Iterable[NullDueGroup], *, max_rows: int = 20) -> None:
    shown = 0
    for grp in groups:
        if shown >= max_rows:
            break
        print(
            f"record_id={grp.record_id} completed={grp.completed} "
            f"null_rows={grp.null_rows} nonnull_rows={grp.nonnull_rows} "
            f"sample_keep_id={grp.sample_keep_id} "
            f"remove_after_exact={grp.remove_count_after_exact}"
        )
        shown += 1


def main() -> None:
    parser = argparse.ArgumentParser(description="Deduplicate Completions rows.")
    parser.add_argument(
        "--db",
        help="Path to sqlite database. Defaults to TklrEnvironment db_path.",
    )
    parser.add_argument(
        "--keep",
        choices=("oldest", "newest"),
        default="oldest",
        help="Which duplicate row to keep per duplicate group. Default: oldest.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Apply deletion. Without this flag, only show what would be removed.",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Create a timestamped backup before applying changes.",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=20,
        help="Show up to this many duplicate groups in the report. Default: 20.",
    )
    parser.add_argument(
        "--collapse-null-due",
        action="store_true",
        help=(
            "Also collapse mixed groups where record_id+completed have both "
            "due=NULL and due=datetime rows. Keeps non-NULL due row(s) and "
            "removes the remaining NULL row after exact dedupe."
        ),
    )
    args = parser.parse_args()

    db_path = _resolve_db_path(args.db)
    if not db_path.exists():
        raise SystemExit(f"Database not found: {db_path}")

    conn = sqlite3.connect(str(db_path))
    try:
        conn.row_factory = sqlite3.Row
        groups = _fetch_duplicate_groups(conn, args.keep)
        dup_groups = len(groups)
        exact_rows_to_remove = sum(g.remove_count for g in groups)
        null_due_groups = (
            _fetch_null_due_groups(conn) if args.collapse_null_due else []
        )
        null_due_group_count = len(null_due_groups)
        null_due_rows_to_remove = sum(
            g.remove_count_after_exact for g in null_due_groups
        )
        rows_to_remove = exact_rows_to_remove + null_due_rows_to_remove

        mode = "APPLY" if args.apply else "DRY-RUN"
        print(f"Mode: {mode}")
        print(f"DB: {db_path}")
        print(f"Exact duplicate groups: {dup_groups}")
        print(f"Rows to remove (exact): {exact_rows_to_remove}")
        if args.collapse_null_due:
            print(f"Mixed NULL/non-NULL due groups: {null_due_group_count}")
            print(
                "Rows to remove (NULL-due collapse, after exact): "
                f"{null_due_rows_to_remove}"
            )
        print(f"Rows to remove (total): {rows_to_remove}")

        if dup_groups:
            print(f"Sample duplicate groups (up to {max(0, args.show)}):")
            _print_groups(groups, max_rows=max(0, args.show))
        if null_due_group_count:
            print(f"Sample NULL-due mixed groups (up to {max(0, args.show)}):")
            _print_null_due_groups(null_due_groups, max_rows=max(0, args.show))

        if not args.apply:
            return

        if rows_to_remove == 0:
            print("No duplicates found; nothing changed.")
            return

        if args.backup:
            ts = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_path = db_path.with_suffix(db_path.suffix + f".bak-{ts}")
            shutil.copy2(db_path, backup_path)
            print(f"Backup written: {backup_path}")

        sql = _build_delete_sql(args.keep)
        null_due_sql = _build_delete_null_due_sql()
        with conn:
            deleted_exact = 0
            if exact_rows_to_remove:
                before = conn.total_changes
                conn.execute(sql)
                deleted_exact = conn.total_changes - before

            deleted_null_due = 0
            if args.collapse_null_due and null_due_group_count:
                before = conn.total_changes
                conn.execute(null_due_sql)
                deleted_null_due = conn.total_changes - before

        deleted = deleted_exact + deleted_null_due
        print(f"Deleted rows (exact): {deleted_exact}")
        if args.collapse_null_due:
            print(f"Deleted rows (NULL-due collapse): {deleted_null_due}")
        print(f"Deleted rows (total): {deleted}")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
