from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_ff_revision_lattice.json"


class RouteB2022FFRevisionEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_all_official_cuts_pass(self):
        self.assertEqual(self.data["archive_count"], 5)
        self.assertTrue(self.data["all_archives_pass"])
        self.assertTrue(all(x["route_b"] >= 85 for x in self.data["archives"]))

    def test_worst_case_margin_is_positive(self):
        self.assertAlmostEqual(
            self.data["route_b"]["min"],
            85.33429175696243,
            places=8,
        )
        self.assertGreater(
            self.data["route_b"]["minimum_margin_above_threshold"],
            0,
        )

    def test_revision_range_is_bounded(self):
        self.assertLess(self.data["size_weakness"]["range"], 1.0)
        self.assertLess(self.data["route_b"]["range"], 0.4)

    def test_2025_and_2026_are_observed_worst_cases(self):
        rows = {x["id"]: x for x in self.data["archives"]}
        self.assertAlmostEqual(
            rows["JULY_2025"]["route_b"],
            self.data["route_b"]["min"],
            places=8,
        )
        self.assertAlmostEqual(
            rows["AUGUST_2026"]["route_b"],
            self.data["route_b"]["min"],
            places=8,
        )

    def test_live_download_evidence_is_recorded(self):
        self.assertTrue(
            self.data["evidence"]["github_actions_live_download_passed"]
        )


if __name__ == "__main__":
    unittest.main()
