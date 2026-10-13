"""Generate a deterministic synthetic 2025 fixed-standard-time power series.

Intentionally removes two hours and repeats one. All values are invented and
not measured energy, production or weather observations.
"""
from __future__ import annotations

import csv
from datetime import datetime, timedelta
from pathlib import Path


def main():
    output = Path(__file__).with_name("synthetic_2025.csv")
    start = datetime(2025, 1, 1)
    missing = {datetime(2025, 3, 9, 2), datetime(2025, 11, 2, 1)}
    with output.open("w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["timestamp", "power_kw"])
        for hour in range(8760):
            instant = start + timedelta(hours=hour)
            if instant in missing:
                continue
            # Invented deterministic non-negative test signal, not a model.
            value = max(0, 100 - abs(instant.hour - 12) * 12)
            writer.writerow([instant.isoformat(), value])
            if instant == datetime(2025, 5, 1, 10):
                writer.writerow([instant.isoformat(), value])
    print(output)


if __name__ == "__main__":
    main()
