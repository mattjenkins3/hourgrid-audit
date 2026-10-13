from __future__ import annotations

import csv
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from zoneinfo import ZoneInfo

from hourgrid_audit import AuditInputError, audit_csv
from hourgrid_audit.core import _parse_hour
from hourgrid_audit.svg import render_svg


class HourgridTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "data.csv"

    def write(self, rows, header=("timestamp", "value", "fold")):
        with self.path.open("w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(header)
            w.writerows(rows)

    def full_year(self, year=2025, basis="fixed", ending=False):
        begin = datetime(year, 1, 1)
        end = datetime(year + 1, 1, 1)
        hours = int((end - begin) / timedelta(hours=1))
        stamps = [begin + timedelta(hours=i + int(ending)) for i in range(hours)]
        if basis == "aware":
            stamps = [x.replace(tzinfo=timezone.utc) for x in stamps]
        return [(x.isoformat(), "3.25", "") for x in stamps]

    def test_complete_fixed_8760(self):
        self.write(self.full_year())
        r = audit_csv(self.path, year=2025, basis="fixed", offset_hours=-7, value_column="value")
        self.assertTrue(r["ok"])
        self.assertEqual((r["expected_hours"], r["observed_unique_hours"], r["rows"]), (8760, 8760, 8760))
        self.assertEqual(sum(m["missing"] for m in r["months"]), 0)

    def test_complete_leap_8784(self):
        self.write(self.full_year(2024))
        r = audit_csv(self.path, year=2024, basis="fixed", offset_hours=-7)
        self.assertEqual(r["expected_hours"], 8784)
        self.assertTrue(r["ok"])

    def test_hour_ending_rollover(self):
        self.write(self.full_year(ending=True))
        r = audit_csv(self.path, year=2025, basis="fixed", offset_hours=0, label="ending")
        self.assertTrue(r["ok"])
        self.assertEqual(r["rows"], 8760)

    def test_missing_duplicate_and_nonmonotonic(self):
        rows = self.full_year()
        rows.pop(35)
        rows.insert(36, rows[2])
        self.write(rows)
        r = audit_csv(self.path, year=2025, basis="fixed", offset_hours=-7)
        self.assertFalse(r["ok"])
        self.assertEqual(r["issue_counts"]["missing_hour"], 1)
        self.assertEqual(r["issue_counts"]["duplicate_hour"], 1)
        self.assertEqual(r["issue_counts"]["non_monotonic"], 1)
        self.assertEqual(r["observed_unique_hours"], 8759)

    def test_aware_accepts_offsets_but_rejects_naive(self):
        self.write(self.full_year(basis="aware"))
        r = audit_csv(self.path, year=2025, basis="aware")
        self.assertTrue(r["ok"])
        self.assertEqual(_parse_hour("2025-01-01T00:00:00-07:00", "aware", timezone.utc, None)[0],
                         datetime(2025, 1, 1, 7, tzinfo=timezone.utc))
        self.assertEqual(_parse_hour("2025-01-01T00:00:00", "aware", timezone.utc, None)[1],
                         "wrong_timezone_basis")

    def test_civil_ambiguous_requires_fold(self):
        tz = ZoneInfo("America/Denver")
        a, err = _parse_hour("2025-11-02T01:00:00", "civil", tz, None)
        self.assertIsNone(a)
        self.assertEqual(err, "ambiguous_local_time")
        a, err = _parse_hour("2025-11-02T01:00:00", "civil", tz, "0")
        b, err2 = _parse_hour("2025-11-02T01:00:00", "civil", tz, "1")
        self.assertIsNone(err)
        self.assertIsNone(err2)
        self.assertEqual(b - a, timedelta(hours=1))

    def test_civil_nonexistent_rejected(self):
        tz = ZoneInfo("America/Denver")
        self.assertEqual(_parse_hour("2025-03-09T02:00:00", "civil", tz, "0")[1],
                         "nonexistent_local_time")

    def test_civil_complete_year_with_fold(self):
        tz = ZoneInfo("America/Denver")
        start = datetime(2025, 1, 1, tzinfo=tz).astimezone(timezone.utc)
        end = datetime(2026, 1, 1, tzinfo=tz).astimezone(timezone.utc)
        hours = int((end - start) / timedelta(hours=1))
        rows = []
        for i in range(hours):
            local = (start + timedelta(hours=i)).astimezone(tz)
            rows.append((local.replace(tzinfo=None).isoformat(), "1", str(local.fold)))
        self.write(rows)
        r = audit_csv(self.path, year=2025, basis="civil", zone="America/Denver", fold_column="fold")
        self.assertTrue(r["ok"])
        self.assertEqual(r["expected_hours"], 8760)
        self.assertEqual(r["months"][2]["expected"], 743)  # spring forward
        self.assertEqual(r["months"][10]["expected"], 721)  # fall back

    def test_half_hour_zone_calendar_alignment(self):
        tz = ZoneInfo("Asia/Kolkata")
        start = datetime(2025, 1, 1, tzinfo=tz).astimezone(timezone.utc)
        self.assertEqual(start.minute, 30)
        self.write(self.full_year())
        r = audit_csv(self.path, year=2025, basis="civil", zone="Asia/Kolkata")
        self.assertTrue(r["ok"])

    def test_offset_aware_off_grid_not_counted(self):
        self.write([("2025-01-01T06:00:00+05:30", "1", "")])
        r = audit_csv(self.path, year=2025, basis="aware")
        self.assertEqual(r["issue_counts"]["off_grid"], 1)
        self.assertEqual(r["observed_unique_hours"], 0)
        self.assertLessEqual(r["coverage_percent"], 100)

    def test_civil_repeated_hour_without_fold_rejected(self):
        self.write([("2025-11-02T01:00:00", "2", ""), ("2025-11-02T01:00:00", "2", "")])
        r = audit_csv(self.path, year=2025, basis="civil", zone="America/Denver")
        self.assertEqual(r["issue_counts"]["ambiguous_local_time"], 2)
        self.assertEqual(r["issue_counts"]["missing_hour"], 8760)

    def test_bad_value_outside_year_and_off_hour(self):
        self.write([
            ("2025-01-01T00:00:00", "nan", ""),
            ("2025-01-01T01:00:00", "", ""),
            ("2025-01-01T02:00:00", "hello", ""),
            ("2025-01-01T02:30:00", "1", ""),
            ("2024-12-31T23:00:00", "1", ""),
        ])
        r = audit_csv(self.path, year=2025, basis="fixed", offset_hours=0, value_column="value")
        for k in ("non_finite_value", "missing_value", "non_numeric_value", "non_hourly", "outside_year"):
            self.assertEqual(r["issue_counts"][k], 1)

    def test_invalid_config_and_header(self):
        self.write(self.full_year()[:2], header=("timestamp", "timestamp", "fold"))
        with self.assertRaises(AuditInputError):
            audit_csv(self.path, year=2025, basis="fixed", offset_hours=0)
        self.write(self.full_year()[:2])
        with self.assertRaises(AuditInputError):
            audit_csv(self.path, year=2025, basis="civil", zone="Invalid/Zone")
        with self.assertRaises(AuditInputError):
            audit_csv(self.path, year=2025, basis="fixed", offset_hours=None)

    def test_samples_capped_and_months_consistent(self):
        self.write([("bad", "5", "") for _ in range(20)])
        r = audit_csv(self.path, year=2025, basis="fixed", offset_hours=0, max_samples=3)
        self.assertEqual(len(r["samples"]), 3)
        self.assertEqual(r["issue_counts"]["parse_error"], 20)
        self.assertEqual(r["issue_counts"]["missing_hour"], 8760)
        self.assertEqual(sum(m["missing"] for m in r["months"]), 8760)
        svg = render_svg(r)
        self.assertIn("Hourly coverage audit", svg)
        self.assertIn("ISSUES DETECTED", svg)
        self.assertEqual(svg.count(" missing</text>"), 12)


if __name__ == "__main__":
    unittest.main()
