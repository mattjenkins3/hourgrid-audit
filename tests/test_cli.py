import contextlib
import csv
from io import StringIO
from pathlib import Path
import tempfile
import unittest

from hourgrid_audit.cli import main


class CliTests(unittest.TestCase):
    def test_exit_codes_and_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            file = root / "a.csv"
            with file.open("w", newline="") as f:
                w = csv.writer(f)
                w.writerow(["timestamp", "power"])
                w.writerow(["2025-01-01T00:00:00", "0"])
            report, svg = root / "report.json", root / "report.svg"
            with contextlib.redirect_stderr(StringIO()):
                self.assertEqual(main([str(file), "--year", "2025", "--basis", "fixed", "--offset-hours", "-7", "--report", str(report), "--svg", str(svg)]), 1)
                self.assertEqual(main([str(file), "--year", "2025", "--basis", "fixed"]), 2)
            self.assertIn('"missing_hour": 8759', report.read_text())
            self.assertIn("<svg", svg.read_text())


if __name__ == "__main__":
    unittest.main()
