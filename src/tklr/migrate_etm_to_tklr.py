#!/usr/bin/env python3
"""
Migrate records from etm.json to tklr database.
Supports --dry-run mode for inspection without DB writes.
"""

import json
from datetime import datetime, timedelta
from dateutil import parser as dtparser
import argparse


# --------------------------------------------------------------------
# Recurrence conversion
# --------------------------------------------------------------------


def recurrence_block(rec: dict) -> str:
    """Convert a single etm recurrence dict into DTSTART/ RRULE/ RDATE/ EXDATE lines."""
    freq_map = {"y": "YEARLY", "m": "MONTHLY", "w": "WEEKLY", "d": "DAILY"}
    parts = []

    if "r" in rec:
        freq = freq_map.get(rec["r"])
        if freq:
            parts.append(f"FREQ={freq}")

    if rec.get("u"):
        until = rec["u"].replace("-", "").replace(":", "")
        parts.append(f"UNTIL={until}")

    if "M" in rec:
        months = ",".join(str(m) for m in rec["M"])
        parts.append(f"BYMONTH={months}")

    if "m" in rec:
        mdays = ",".join(str(m) for m in rec["m"])
        parts.append(f"BYMONTHDAY={mdays}")

    if "w" in rec:
        daymap = ["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
        bydays = ",".join(daymap[d] for d in rec["w"])
        parts.append(f"BYDAY={bydays}")

    if "h" in rec:
        hours = ",".join(str(h) for h in rec["h"])
        parts.append(f"BYHOUR={hours}")

    lines = []
    if parts:
        lines.append("RRULE:" + ";".join(parts))

    if rec.get("s"):
        dtstart = rec["s"].replace("-", "").replace(":", "")
        if len(dtstart) == 8:
            lines.insert(0, f"DTSTART;VALUE=DATE:{dtstart}")
        else:
            lines.insert(0, f"DTSTART:{dtstart}")

    if "+" in rec:
        rdates = [raw.replace("-", "").replace(":", "") for raw in rec["+"]]
        lines.append("RDATE:" + ",".join(rdates))

    if "-" in rec:
        exdates = [raw.replace("-", "").replace(":", "") for raw in rec["-"]]
        lines.append("EXDATE:" + ",".join(exdates))

    return "\n".join(lines)


def recurrence_set(rec_field) -> str:
    """Handle single or multiple recurrence dicts into one rruleset string."""
    blocks = []
    if isinstance(rec_field, list):
        for r in rec_field:
            blocks.append(recurrence_block(r))
    elif isinstance(rec_field, dict):
        blocks.append(recurrence_block(rec_field))
    return "\n".join(blocks)


# --------------------------------------------------------------------
# Converter
# --------------------------------------------------------------------


class EtmToTklrConverter:
    FIELD_MAP = {
        "itemtype": "itemtype",
        "summary": "subject",
        "d": "description",
        "b": "beginby",
        "t": "tags",
        "l": "context",
        "i": "context",  # path, mapped to context
        "j": "jobs",  # jobs JSON
        "created": "created",
    }

    def __init__(self):
        self.errors = []

    def convert_record(self, etm_record: dict):
        """Return (tklr_dict, completions)."""
        tklr_record = {}
        completions = []

        # Simple mapped fields
        for old_key, new_key in self.FIELD_MAP.items():
            if old_key in etm_record:
                tklr_record[new_key] = etm_record[old_key]

        # Start datetime
        if "s" in etm_record:
            dt = self._parse_etm_time(etm_record["s"])
            if dt:
                tklr_record["dtstart_str"] = f"DTSTART:{dt.strftime('%Y%m%dT%H%M%S')}"
                tklr_record["rdstart_str"] = f"RDATE:{dt.strftime('%Y%m%dT%H%M%S')}"

        # Extent
        if "e" in etm_record:
            td = self._parse_etm_interval(etm_record["e"])
            if td:
                tklr_record["extent"] = str(td)

        # Recurrence
        if "r" in etm_record:
            tklr_record["rruleset"] = recurrence_set(etm_record["r"])

        # Jobs
        if "j" in etm_record:
            tklr_record["jobs"] = json.dumps(etm_record["j"])

        # Completions from "f"
        if "f" in etm_record:
            try:
                raw = etm_record["f"]
                parts = raw.split("->")
                if len(parts) == 2:
                    due_dt = self._parse_etm_time(parts[0].split(":")[1].strip())
                    completed_dt = self._parse_etm_time(parts[1].strip())
                    if completed_dt:
                        completions.append((completed_dt, due_dt))
            except Exception as e:
                self.errors.append(("f", str(e), etm_record))

        # Completions from "u"
        if "u" in etm_record:
            for u in etm_record["u"]:
                try:
                    completed_dt = None
                    for val in u:
                        if val.startswith("{T}:"):
                            completed_dt = self._parse_etm_time(val)
                    if completed_dt:
                        completions.append((completed_dt, None))
                except Exception as e:
                    self.errors.append(("u", str(e), etm_record))

        return tklr_record, completions

    def _parse_etm_time(self, raw: str):
        """Parse etm datetime string like '{T}:20250327T2030A'."""
        try:
            s = raw.split(":", 1)[1]
            return dtparser.parse(s)
        except Exception:
            return None

    def _parse_etm_interval(self, raw: str):
        """Parse etm interval string like '{I}:45m'."""
        try:
            s = raw.split(":", 1)[1]
            if s.endswith("m"):
                return timedelta(minutes=int(s[:-1]))
            if s.endswith("h"):
                return timedelta(hours=int(s[:-1]))
            if s.endswith("d"):
                return timedelta(days=int(s[:-1]))
        except Exception:
            return None


# --------------------------------------------------------------------
# Migration Runner
# --------------------------------------------------------------------


def migrate(filepath, controller, model, Item):
    with open(filepath, "r") as f:
        etm_data = json.load(f)

    converter = EtmToTklrConverter()
    imported = 0
    for etm_id, etm_record in etm_data.items():
        tklr_dict, completions = converter.convert_record(etm_record)

        try:
            item = Item(**tklr_dict)
            record_id = controller.add_item(item)
            for completed_dt, due_dt in completions:
                model.add_completion(record_id, None, (completed_dt, due_dt))
            imported += 1
        except Exception as e:
            print(f"❌ Failed to import record {etm_id}: {e}")

    print(f"✅ Imported {imported} records from {filepath}")
    if converter.errors:
        print(f"⚠️ Encountered {len(converter.errors)} conversion errors")


def migrate(filepath, controller, model, Item, dry_run=False, limit=None):
    with open(filepath, "r") as f:
        etm_data = json.load(f)

    converter = EtmToTklrConverter()
    imported = 0

    for idx, (etm_id, etm_record) in enumerate(etm_data.items()):
        if limit and idx >= limit:
            break

        tklr_dict, completions = converter.convert_record(etm_record)

        if dry_run:
            print(f"--- Record {etm_id} ---")
            print(json.dumps(tklr_dict, indent=2, default=str))
            if completions:
                print("  Completions:")
                for comp in completions:
                    print(f"    completed={comp[0]} due={comp[1]}")
            print()
            imported += 1
            continue

        try:
            item = Item(**tklr_dict)
            record_id = controller.add_item(item)
            for completed_dt, due_dt in completions:
                model.add_completion(record_id, None, (completed_dt, due_dt))
            imported += 1
        except Exception as e:
            print(f"❌ Failed to import record {etm_id}: {e}")

    print(f"✅ Processed {imported} records from {filepath}")
    if converter.errors:
        print(f"⚠️ Encountered {len(converter.errors)} conversion errors")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate etm.json → tklr")
    parser.add_argument("filepath", help="Path to etm.json")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print converted records without writing to DB",
    )
    parser.add_argument(
        "--limit", type=int, help="Limit number of records processed (for testing)"
    )
    args = parser.parse_args()

    # Example placeholder usage:
    # from myapp import controller, model, Item
    # migrate(args.filepath, controller, model, Item,
    #         dry_run=args.dry_run, limit=args.limit)

    print("⚠️ This script must be integrated with your tklr environment.")
    print("   Import controller, model, and Item, then call migrate().")
