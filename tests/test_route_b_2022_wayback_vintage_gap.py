from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_wayback_vintage_gap.json"


class RouteB2022WaybackVintageGapTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_gap_is_archive_coverage_not_access_failure(self):
        self.assertEqual(
            self.data["status"],
            "NO_PRE_CUTOFF_SNAPSHOT_WITH_202111",
        )
        self.assertEqual(self.data["errors"], [])

    def test_latest_wayback_snapshot_is_too_old(self):
        x = self.data["latest_usable_snapshot"]
        self.assertEqual(x["timestamp"], "20210413020542")
        self.assertEqual(x["last_month"], "202102")
        self.assertFalse(x["has_202111"])

    def test_exact_vintage_remains_unresolved(self):
        self.assertFalse(self.data["exact_or_pre_cutoff_vintage"])


if __name__ == "__main__":
    unittest.main()
