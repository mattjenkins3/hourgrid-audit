"""Command-line interface for hourly coverage and DST contract checks."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .core import AuditInputError, audit_csv
from .svg import render_svg


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Audit a declared calendar year of hourly CSV timestamps without guessing timezone or DST")
    parser.add_argument("csv", type=Path, help="CSV with an ISO8601 timestamp column")
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--basis", required=True, choices=("aware", "fixed", "civil"))
    parser.add_argument("--zone", help="IANA zone required for civil input, e.g. America/Denver")
    parser.add_argument("--offset-hours", type=int, help="fixed local standard time UTC offset")
    parser.add_argument("--label", choices=("beginning", "ending"), default="beginning")
    parser.add_argument("--timestamp-column", default="timestamp")
    parser.add_argument("--fold-column", help="0/1 field required for ambiguous civil timestamps")
    parser.add_argument("--value-column", help="optional numeric field; checks blanks, NaN, inf")
    parser.add_argument("--report", type=Path, help="write deterministic JSON report here (otherwise stdout)")
    parser.add_argument("--svg", type=Path, help="write standalone SVG monthly coverage dashboard")
    args = parser.parse_args(argv)
    try:
        report = audit_csv(
            args.csv, year=args.year, basis=args.basis, zone=args.zone,
            offset_hours=args.offset_hours, timestamp_column=args.timestamp_column,
            fold_column=args.fold_column, value_column=args.value_column, label=args.label,
        )
        payload = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.report:
            args.report.write_text(payload, encoding="utf-8")
        else:
            sys.stdout.write(payload)
        if args.svg:
            args.svg.write_text(render_svg(report), encoding="utf-8")
        print(f"{'PASS' if report['ok'] else 'FAIL'}: {report['observed_unique_hours']}/{report['expected_hours']} expected hourly slots; {sum(report['issue_counts'].values())} issues", file=sys.stderr)
        return 0 if report["ok"] else 1
    except (AuditInputError, OSError) as exc:
        print(f"INPUT ERROR: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
