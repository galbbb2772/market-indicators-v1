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
            "WAYBACK_CAPTURE_GAP_FACTOR_VINTAGE_CONTENT_RECOVERED_ELSEWHERE",
        )
        self.assertEqual(self.data["errors"], [])
        recovered = self.data["official_dec2021_factor_vintage"]
        self.assertEqual(
            recovered["status"],
            "RECOVERED_OFFICIAL_DEC2021_VINTAGE_CONTENT",
        )
        self.assertEqual(recovered["last_month"], "202111")
        self.assertTrue(recovered["pass"])

    def test_latest_wayback_capture_is_too_old(self):
        self.assertEqual(
            self.data["schema_version"],
            "route-b-2022-wayback-vintage-gap-2",
        )
        x = self.data["latest_usable_capture"]
        self.assertEqual(x["timestamp"], "20210413020542")
        self.assertEqual(x["max_last_month"], "202102")
        self.assertEqual(
            x["observed_digest"],
            "EFKVXSQUQYCV73HEGEYBAHTQBIGZDSKZ",
        )
        self.assertFalse(x["has_202111"])

    def test_exact_vintage_remains_unresolved(self):
        self.assertFalse(self.data["exact_or_pre_cutoff_vintage"])


if __name__ == "__main__":
    unittest.main()
