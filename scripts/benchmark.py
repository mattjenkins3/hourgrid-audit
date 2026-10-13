"""Repeatable *local* runtime measurement; not a competitive benchmark."""
from __future__ import annotations

import argparse
import platform
from statistics import median
from time import perf_counter
from hourgrid_audit import audit_csv


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("csv")
    p.add_argument("--repeats", type=int, default=15)
    a = p.parse_args()
    if not 1 <= a.repeats <= 100:
        p.error("repeats must be 1..100")
    results = []
    for _ in range(a.repeats):
        start = perf_counter()
        audit_csv(a.csv, year=2025, basis="fixed", offset_hours=-7, value_column="power_kw")
        results.append(perf_counter() - start)
    print(f"Python {platform.python_version()} | {a.repeats} runs | median={median(results):.4f}s min={min(results):.4f}s max={max(results):.4f}s")


if __name__ == "__main__":
    main()
