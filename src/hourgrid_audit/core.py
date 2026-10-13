"""Strict, non-mutating audits of hourly CSV timestamp contracts.

All comparisons occur on UTC hour-start instants. The caller MUST declare
whether input timestamps are UTC/offset-aware, fixed-offset naive, or IANA
civil naive; the library never guesses timezone, DST fold or hour labeling.
"""
from __future__ import annotations

import csv
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import math
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

UTC = timezone.utc
HOUR = timedelta(hours=1)
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


class AuditInputError(ValueError):
    """An invalid audit configuration or input schema (exit status 2)."""


def _config(year: int, basis: str, zone: str | None, offset_hours: int | None):
    if type(year) is not int or not 1900 <= year <= 2100:
        raise AuditInputError("year must be an integer between 1900 and 2100")
    if basis not in ("aware", "fixed", "civil"):
        raise AuditInputError("basis must be aware, fixed, or civil")
    if basis == "aware":
        if zone is not None or offset_hours is not None:
            raise AuditInputError("aware basis accepts neither --zone nor --offset-hours")
        return UTC
    if basis == "fixed":
        if zone is not None or type(offset_hours) is not int or not -12 <= offset_hours <= 14:
            raise AuditInputError("fixed basis requires --offset-hours (-12..14), not --zone")
        return timezone(timedelta(hours=offset_hours))
    if not isinstance(zone, str) or not zone or offset_hours is not None:
        raise AuditInputError("civil basis requires --zone, not --offset-hours")
    try:
        return ZoneInfo(zone)
    except (ZoneInfoNotFoundError, ValueError) as exc:
        raise AuditInputError(f"unknown IANA timezone: {zone}") from exc


def _parse_hour(text: str, basis: str, tz, fold_text: str | None):
    """Return (UTC hour start candidate, error code or None).

    Aware ISO8601 timestamps are required for `aware`. For civil input, an
    ambiguous wall-clock time requires an explicit 0/1 fold CSV column.
    Nonexistent local times are always rejected, never silently shifted.
    """
    if not isinstance(text, str) or not text.strip():
        return None, "parse_error"
    if "T" not in text and " " not in text:
        return None, "parse_error"
    try:
        dt = datetime.fromisoformat(text.strip().replace("Z", "+00:00"))
    except ValueError:
        return None, "parse_error"
    if dt.minute != 0 or dt.second != 0 or dt.microsecond != 0:
        return None, "non_hourly"
    if basis == "aware":
        if dt.tzinfo is None or dt.utcoffset() is None:
            return None, "wrong_timezone_basis"
        if fold_text not in (None, ""):
            return None, "bad_fold"
        return dt.astimezone(UTC), None
    if dt.tzinfo is not None:
        return None, "wrong_timezone_basis"
    if basis == "fixed":
        if fold_text not in (None, ""):
            return None, "bad_fold"
        return dt.replace(tzinfo=tz).astimezone(UTC), None

    if fold_text not in (None, "", "0", "1"):
        return None, "bad_fold"
    # Round-trip both folds: detects nonexistent local time, and whether the
    # same wall time maps to two distinct real instants.
    valid: dict[int, datetime] = {}
    for fold in (0, 1):
        utc = dt.replace(tzinfo=tz, fold=fold).astimezone(UTC)
        if utc.astimezone(tz).replace(tzinfo=None) == dt:
            valid[fold] = utc
    if not valid:
        return None, "nonexistent_local_time"
    if len(set(valid.values())) == 2:
        if fold_text not in ("0", "1"):
            return None, "ambiguous_local_time"
        return valid[int(fold_text)], None
    if fold_text == "1":
        return None, "bad_fold"
    return next(iter(valid.values())), None


def audit_csv(
    path: str | Path, *, year: int, basis: str,
    zone: str | None = None, offset_hours: int | None = None,
    timestamp_column: str = "timestamp", fold_column: str | None = None,
    value_column: str | None = None, label: str = "beginning", max_samples: int = 18,
) -> dict:
    """Audit a complete declared calendar year of hourly timestamps in CSV.

    Returns JSON-compatible, deterministic counts and capped issue examples.
    No interpolation, time conversion of source files, or inferred DST policy.
    """
    tz = _config(year, basis, zone, offset_hours)
    if label not in ("beginning", "ending"):
        raise AuditInputError("label must be beginning or ending")
    if type(max_samples) is not int or not 0 <= max_samples <= 100:
        raise AuditInputError("max_samples must be 0..100")
    for column in (timestamp_column, fold_column, value_column):
        if column is not None and (not isinstance(column, str) or not column.strip()):
            raise AuditInputError("column names must be nonempty")
    if len(set(x for x in (timestamp_column, fold_column, value_column) if x)) != len(
        [x for x in (timestamp_column, fold_column, value_column) if x]
    ):
        raise AuditInputError("timestamp, fold and value columns must be distinct")

    start = datetime(year, 1, 1, tzinfo=tz).astimezone(UTC)
    stop = datetime(year + 1, 1, 1, tzinfo=tz).astimezone(UTC)
    if (stop - start).total_seconds() % 3600:
        raise AuditInputError("calendar-year duration does not contain a whole number of hours")
    expected_hours = int((stop - start) / HOUR)
    if not 8700 <= expected_hours <= 8850:
        raise AuditInputError("calendar-year duration outside supported hourly range")

    counts: Counter[str] = Counter()
    samples: list[dict] = []
    seen: set[datetime] = set()
    row_count = 0
    parsed_rows = 0
    previous: datetime | None = None

    def issue(code: str, row: int | None, timestamp: str, detail: str = ""):
        counts[code] += 1
        if len(samples) < max_samples:
            samples.append({"code": code, "row": row, "timestamp": timestamp, "detail": detail})

    path = Path(path)
    try:
        digest = hashlib.sha256()
        with path.open("rb") as raw_file:
            for chunk in iter(lambda: raw_file.read(1024 * 1024), b""):
                digest.update(chunk)
        source_sha256 = digest.hexdigest()
        with path.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            names = reader.fieldnames
            if not names or any(not n for n in names) or len(set(names)) != len(names):
                raise AuditInputError("CSV must have a header with unique nonempty column names")
            required = [timestamp_column] + [x for x in (fold_column, value_column) if x]
            if not set(required).issubset(names):
                raise AuditInputError(f"CSV is missing required columns: {sorted(set(required) - set(names))}")
            for row_num, record in enumerate(reader, start=2):
                row_count += 1
                raw = record.get(timestamp_column) or ""
                if None in record:
                    issue("malformed_row", row_num, raw, "too many CSV fields")
                    continue
                instant, error = _parse_hour(raw, basis, tz, record.get(fold_column) if fold_column else None)
                if error:
                    issue(error, row_num, raw)
                    continue
                assert instant is not None
                if label == "ending":
                    instant -= HOUR
                parsed_rows += 1
                if previous is not None and instant < previous:
                    issue("non_monotonic", row_num, raw, "UTC hour-start earlier than previous parsed row")
                previous = instant
                if not start <= instant < stop:
                    issue("outside_year", row_num, raw, "normalized hour lies outside declared calendar year")
                    continue
                if (instant - start) % HOUR != timedelta(0):
                    issue("off_grid", row_num, raw, "normalized instant does not align with expected hourly grid")
                    continue
                if instant in seen:
                    issue("duplicate_hour", row_num, raw, "duplicate UTC hour-start instant")
                seen.add(instant)
                if value_column:
                    value = record.get(value_column)
                    if value is None or not value.strip():
                        issue("missing_value", row_num, raw, value_column)
                    else:
                        try:
                            numeric = float(value)
                        except ValueError:
                            issue("non_numeric_value", row_num, raw, value)
                        else:
                            if not math.isfinite(numeric):
                                issue("non_finite_value", row_num, raw, value)
    except (OSError, UnicodeError, csv.Error) as exc:
        raise AuditInputError(f"unable to read CSV: {exc}") from exc

    expected_by_month = [0] * 12
    observed_by_month = [0] * 12
    expected = set()
    for h in range(expected_hours):
        slot = start + h * HOUR
        expected.add(slot)
        expected_by_month[slot.astimezone(tz).month - 1] += 1
    for slot in seen:
        observed_by_month[slot.astimezone(tz).month - 1] += 1
    missing = sorted(expected - seen)
    counts["missing_hour"] += len(missing)
    for slot in missing[: max(0, max_samples - len(samples))]:
        issue("_sample_only_missing", None, slot.isoformat(), "missing normalized UTC hour")
    counts.pop("_sample_only_missing", None)
    for item in samples:
        if item["code"] == "_sample_only_missing":
            item["code"] = "missing_hour"

    months = [
        {"month": name, "expected": expected_by_month[i],
         "observed": observed_by_month[i],
         "missing": expected_by_month[i] - observed_by_month[i]}
        for i, name in enumerate(MONTHS)
    ]
    return {
        "schema": "hourgrid-audit-v1", "source_sha256": source_sha256,
        "year": year, "basis": basis, "zone": zone, "offset_hours": offset_hours,
        "label": label, "timestamp_column": timestamp_column,
        "fold_column": fold_column, "value_column": value_column,
        "rows": row_count, "parsed_rows": parsed_rows,
        "expected_hours": expected_hours, "observed_unique_hours": len(seen),
        "coverage_percent": round(100 * len(seen) / expected_hours, 5),
        "issue_counts": dict(sorted((k, v) for k, v in counts.items() if v)),
        "ok": not any(counts.values()), "months": months, "samples": samples,
    }
