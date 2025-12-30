from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Callable, Iterable, List, Sequence

from dateutil import parser as dt_parser

FIELD_REGEX_DATE = re.compile(r"^\d{4}-\d{1,2}-\d{1,2}$")
LIST_SPLIT_PATTERN = re.compile(r"[,\s]+")


class QueryError(ValueError):
    """Raised when a query string cannot be parsed."""


@dataclass(frozen=True)
class QueryMatch:
    record_id: int
    itemtype: str
    subject: str


@dataclass
class QueryResponse:
    matches: list[QueryMatch]
    info_id: int | None = None


class QueryPlan:
    def __init__(self, clauses: list[tuple[str | None, Callable[["RecordView"], bool]]]):
        self.clauses = clauses

    def matches(self, record: "RecordView") -> bool:
        """
        Evaluate the compiled plan against a record, applying each predicate in
        sequence while honoring the stored ``and``/``or`` connectors.  Clauses
        default to ``and`` when no connector is provided (first clause).
        """
        result: bool | None = None
        for connector, predicate in self.clauses:
            value = predicate(record)
            if result is None:
                result = value
                continue
            if connector == "or":
                result = result or value
            else:
                result = result and value
        return bool(result)

    @property
    def is_empty(self) -> bool:
        return not self.clauses


class RecordView:
    """Normalized view over a record's tokens for querying."""

    def __init__(
        self,
        record_id: int,
        itemtype: str,
        subject: str,
        tokens: Sequence[dict],
    ) -> None:
        self.record_id = record_id
        self.itemtype = (itemtype or "").strip()
        self.subject = (subject or "").strip()
        self._field_map: dict[str, list[str]] = {}
        self._populate_from_tokens(tokens or [])

    def _populate_from_tokens(self, tokens: Sequence[dict]) -> None:
        self._field_map["itemtype"] = [self.itemtype]
        self._field_map["subject"] = [self.subject]
        for token in tokens:
            if token.get("t") == "@":
                key = (token.get("k") or "").lower()
                if not key:
                    continue
                if key == "m":
                    self._field_map.setdefault("m", []).append("[masked]")
                    continue
                value = self._extract_token_value(token)
                if value is None:
                    continue
                self._field_map.setdefault(key, []).append(value)
            elif token.get("t") == "subject":
                text = (token.get("token") or "").strip()
                if text:
                    self._field_map["subject"].append(text)

    def _extract_token_value(self, token: dict) -> str | None:
        raw = token.get("token")
        if not raw:
            return None
        raw = str(raw).strip()
        key = token.get("k") or ""
        prefix = f"@{key}"
        if raw.startswith(prefix):
            value = raw[len(prefix) :].strip()
        else:
            value = raw
        return value

    def get_values(self, field: str) -> list[str]:
        field = normalize_field(field)
        return list(self._field_map.get(field, []))

    def get_list_values(self, field: str) -> list[str]:
        values: list[str] = []
        for value in self.get_values(field):
            parts = [part.strip() for part in LIST_SPLIT_PATTERN.split(value) if part]
            values.extend(parts)
        return values

    def get_datetime_values(self, field: str) -> list[tuple[date | datetime, bool]]:
        parsed: list[tuple[date | datetime, bool]] = []
        for value in self.get_values(field):
            parsed_value = parse_field_datetime(value)
            if parsed_value is not None:
                parsed.append(parsed_value)
        return parsed


class QueryParser:
    """Parse query text into a QueryPlan."""

    def __init__(self) -> None:
        self._builders: dict[str, Callable[[list[str]], Callable[[RecordView], bool]]] = {
            "begins": self._build_begins,
            "includes": self._build_includes,
            "in": self._build_includes,
            "equals": self._build_equals,
            "more": self._build_more,
            "less": self._build_less,
            "exists": self._build_exists,
            "any": self._build_any,
            "all": self._build_all,
            "one": self._build_one,
            "dt": self._build_dt,
        }

    def parse(self, text: str) -> tuple[QueryPlan, int | None]:
        """
        Parse the mini query DSL into executable predicates.

        Grammar (simplified):
            query := clause ( (AND|OR) clause )*
            clause := [~] command args...
            command := begins|includes|equals|...|dt|info
            args depend on command (see help text)

        Special cases:
            • ``info <id>`` short-circuits and returns the requested record id.
            • Prefixing a command with ``~`` negates the resulting predicate.

        Tokens are whitespace-delimited; connectors must be lowercase ``and``/``or``.
        """
        text = (text or "").strip()
        if not text:
            raise QueryError("Enter a query.")
        tokens = text.split()
        clauses: list[tuple[str | None, Callable[[RecordView], bool]]] = []
        connector: str | None = None
        info_id: int | None = None
        idx = 0

        while idx < len(tokens):
            token = tokens[idx]
            lowered = token.lower()
            if lowered in ("and", "or"):
                if connector is not None:
                    raise QueryError("Two connectors in a row are not allowed.")
                connector = lowered
                idx += 1
                continue

            negate = False
            if token.startswith("~") and len(token) > 1:
                negate = True
                token = token[1:]
                lowered = token.lower()

            if lowered == "info":
                if clauses:
                    raise QueryError("The 'info' command cannot be combined with other predicates.")
                idx += 1
                if idx >= len(tokens):
                    raise QueryError("Missing id for 'info'.")
                try:
                    info_id = int(tokens[idx])
                except ValueError as exc:
                    raise QueryError("Record id must be an integer.") from exc
                return QueryPlan([]), info_id

            builder = self._builders.get(lowered)
            if not builder:
                raise QueryError(f"Unknown command: {token}")

            idx += 1
            args: list[str] = []
            while idx < len(tokens):
                peek = tokens[idx]
                if peek.lower() in ("and", "or"):
                    break
                args.append(peek)
                idx += 1

            predicate = builder(args)
            if negate:
                predicate = negate_predicate(predicate)

            clause_connector = connector if clauses else None
            clauses.append((clause_connector, predicate))
            connector = None

        if connector is not None:
            raise QueryError("Query cannot end with a connector.")

        return QueryPlan(clauses), info_id

    def _build_begins(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("begins requires a field and a pattern.")
        fields = args[:-1]
        pattern = compile_regex(args[-1])

        def predicate(record: RecordView) -> bool:
            for field in fields:
                for value in record.get_values(field):
                    if pattern.match(value or ""):
                        return True
            return False

        return predicate

    def _build_includes(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("includes requires at least one field and a pattern.")
        fields = args[:-1]
        pattern = compile_regex(args[-1])

        def predicate(record: RecordView) -> bool:
            for field in fields:
                for value in record.get_values(field):
                    if pattern.search(value or ""):
                        return True
            return False

        return predicate

    def _build_equals(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("equals requires a field and a value.")
        field = args[0]
        target = args[1]

        def predicate(record: RecordView) -> bool:
            return any(value == target for value in record.get_values(field))

        return predicate

    def _build_more(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("more requires a field and a value.")
        field = args[0]
        target = args[1]

        def predicate(record: RecordView) -> bool:
            for value in record.get_values(field):
                if compare_values(value, target, ">="):
                    return True
            return False

        return predicate

    def _build_less(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("less requires a field and a value.")
        field = args[0]
        target = args[1]

        def predicate(record: RecordView) -> bool:
            for value in record.get_values(field):
                if compare_values(value, target, "<="):
                    return True
            return False

        return predicate

    def _build_exists(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) != 1:
            raise QueryError("exists requires exactly one field.")
        field = args[0]

        def predicate(record: RecordView) -> bool:
            return any((value or "").strip() for value in record.get_values(field))

        return predicate

    def _build_any(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("any requires a field followed by values.")
        field = args[0]
        values = args[1:]

        def predicate(record: RecordView) -> bool:
            field_values = set(record.get_list_values(field))
            return any(value in field_values for value in values)

        return predicate

    def _build_all(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("all requires a field followed by values.")
        field = args[0]
        values = args[1:]

        def predicate(record: RecordView) -> bool:
            field_values = set(record.get_list_values(field))
            return all(value in field_values for value in values)

        return predicate

    def _build_one(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("one requires a field followed by values.")
        field = args[0]
        values = args[1:]

        def predicate(record: RecordView) -> bool:
            field_values = record.get_values(field)
            return any(value in values for value in field_values)

        return predicate

    def _build_dt(self, args: list[str]) -> Callable[[RecordView], bool]:
        if len(args) < 2:
            raise QueryError("dt requires a field and expression.")
        field = args[0]
        operator = args[1]

        if operator == "?" and len(args) >= 3:
            kind = args[2].lower()
            if kind not in ("date", "time"):
                raise QueryError("dt ? expects 'date' or 'time'.")

            def predicate(record: RecordView) -> bool:
                values = record.get_datetime_values(field)
                if kind == "date":
                    return any(is_date_only for _, is_date_only in values)
                return any(not is_date_only for _, is_date_only in values)

            return predicate

        if operator not in (">", "<", "="):
            raise QueryError("dt comparison must use '>', '<', or '='.")
        if len(args) < 3:
            raise QueryError("dt comparison missing value.")
        target_value = parse_query_datetime(args[2])

        def predicate(record: RecordView) -> bool:
            values = record.get_datetime_values(field)
            for value, is_date_only in values:
                record_value = value.date() if is_date_only and isinstance(value, datetime) else value
                target = (
                    target_value.date()
                    if is_date_only and isinstance(target_value, datetime)
                    else target_value
                )
                if compare_dates(record_value, target, operator):
                    return True
            return False

        return predicate


class QueryEngine:
    """Entry point to parse and evaluate queries."""

    def __init__(self) -> None:
        self.parser = QueryParser()

    def run(
        self,
        text: str,
        records: Iterable[dict],
    ) -> QueryResponse:
        plan, info_id = self.parser.parse(text)
        if info_id is not None:
            return QueryResponse(matches=[], info_id=info_id)

        matches: list[QueryMatch] = []
        for record in records:
            view = RecordView(
                record_id=record.get("id", 0),
                itemtype=record.get("itemtype", ""),
                subject=record.get("subject", ""),
                tokens=record.get("tokens", []),
            )
            if plan.matches(view):
                matches.append(
                    QueryMatch(
                        record_id=view.record_id,
                        itemtype=view.itemtype,
                        subject=view.subject or "(untitled)",
                    )
                )
        return QueryResponse(matches=matches, info_id=None)


def compile_regex(pattern: str) -> re.Pattern[str]:
    try:
        return re.compile(pattern, flags=re.IGNORECASE)
    except re.error as exc:
        raise QueryError(f"Invalid regular expression: {pattern}") from exc


def normalize_field(name: str) -> str:
    name = (name or "").strip().lower()
    if name.startswith("@"):
        name = name[1:]
    if name in ("subject", "summary"):
        return "subject"
    if name in ("itemtype", "type", "item"):
        return "itemtype"
    return name


def negate_predicate(predicate: Callable[[RecordView], bool]) -> Callable[[RecordView], bool]:
    def _wrapped(record: RecordView) -> bool:
        return not predicate(record)

    return _wrapped


def compare_values(left: str, right: str, operator: str) -> bool:
    left_num = to_number(left)
    right_num = to_number(right)

    if left_num is not None and right_num is not None:
        lhs = left_num
        rhs = right_num
    else:
        lhs = left or ""
        rhs = right or ""

    if operator == ">=":
        return lhs >= rhs
    if operator == "<=":
        return lhs <= rhs
    raise QueryError(f"Unsupported comparison operator: {operator}")


def to_number(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_field_datetime(value: str) -> tuple[date | datetime, bool] | None:
    raw = (value or "").strip()
    if not raw:
        return None
    try:
        parsed = dt_parser.parse(raw)
    except Exception:
        return None
    is_date_only = bool(FIELD_REGEX_DATE.fullmatch(raw))
    if is_date_only:
        return (parsed.date(), True)
    return (parsed, False)


def parse_query_datetime(text: str) -> date | datetime:
    parts = [p.strip() for p in text.split("-") if p.strip()]
    if len(parts) < 3:
        raise QueryError("Datetime comparisons require yyyy-mm-dd or yyyy-mm-dd-HH-MM.")
    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
    except ValueError as exc:
        raise QueryError("Datetime components must be numeric.") from exc

    if len(parts) == 3:
        return date(year, month, day)

    try:
        hour = int(parts[3])
        minute = int(parts[4]) if len(parts) > 4 else 0
    except ValueError as exc:
        raise QueryError("Time components must be numeric.") from exc
    return datetime(year, month, day, hour, minute)


def compare_dates(
    record_value: date | datetime,
    target_value: date | datetime,
    operator: str,
) -> bool:
    if isinstance(record_value, datetime) and isinstance(target_value, date):
        target_value = datetime(
            target_value.year,
            target_value.month,
            target_value.day,
            0,
            0,
        )
    if isinstance(record_value, date) and isinstance(target_value, datetime):
        record_value = datetime(
            record_value.year,
            record_value.month,
            record_value.day,
            0,
            0,
        )

    if operator == ">":
        return record_value > target_value
    if operator == "<":
        return record_value < target_value
    if operator == "=":
        return record_value == target_value
    raise QueryError(f"Unsupported datetime operator: {operator}")
