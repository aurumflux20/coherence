"""Health report helpers — no nested full health (avoids recursion)."""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from coherence.health import CheckResult, HealthReport, plain_english, write_report


class TestHealth(unittest.TestCase):
    def test_report_json_and_next(self):
        report = HealthReport(
            ok=True,
            checked_at=1.0,
            checks=[CheckResult("law", True, "ok", 0.01)],
            next_action="health green — ship depth only with storm still green",
            version="0.5.1",
        )
        self.assertTrue(report.ok)
        text = plain_english(report)
        self.assertIn("GREEN", text)
        self.assertIn("NEXT:", text)
        path = Path(tempfile.mkdtemp()) / "h.json"
        write_report(report, path)
        data = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(data["ok"])
        self.assertEqual(data["version"], "0.5.1")

    def test_red_report(self):
        report = HealthReport(
            ok=False,
            checked_at=1.0,
            checks=[CheckResult("storm", False, "boom", 0.1)],
            next_action="fix storm",
            version="0.5.1",
        )
        self.assertIn("RED", plain_english(report))


if __name__ == "__main__":
    unittest.main()
