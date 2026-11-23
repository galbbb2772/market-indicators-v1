from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_ff_revision_sensitivity.json"


class RouteB2022FFRevisionSensitivityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_exact_vintage_is_not_overclaimed(self):
        self.assertFalse(
            self.data["official_archive_note"]["exact_2022_01_03_vintage_recovered"]
        )
        self.assertIn("EXACT_VINTAGE_UNRESOLVED", self.data["status"])

    def test_all_sampled_variants_still_pass_85(self):
        for row in self.data["variants"]:
            self.assertTrue(row["passes"])
            self.assertGreaterEqual(row["route_b"], 85.0)

    def test_observed_revision_range_stays_above_failure_boundary(self):
        r = self.data["observed_range"]
        self.assertGreater(r["size_weakness_min"], self.data["critical_size_weakness"])
        self.assertGreater(r["route_b_min"], self.data["route_b_threshold"])

    def test_no_threshold_change(self):
        self.assertEqual(self.data["route_b_threshold"], 85)


if __name__ == "__main__":
    unittest.main()
