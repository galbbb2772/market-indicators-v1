from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"research"/"route_b_2022_ff_dec2021_wayback_exact_evidence.json"


class RouteB2022FFDec2021WaybackExactEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=json.loads(PATH.read_text(encoding="utf-8"))

    def test_wayback_exact_url_has_no_pre_cutoff_capture(self):
        x=self.data
        self.assertEqual(x["snapshot_count"],0)
        self.assertFalse(x["exact_sha_capture_found"])
        self.assertFalse(x["pre_cutoff_vintage_capture_found"])
        self.assertEqual(x["errors"],[])

    def test_factor_vintage_content_remains_recovered(self):
        x=self.data["recovered_official_vintage"]
        self.assertEqual(x["crsp_database"],"202111")
        self.assertEqual(x["last_month"],"202111")
        self.assertTrue(x["passes"])
        self.assertGreater(x["route_b"],85)

    def test_gap_is_delivery_provenance_only(self):
        x=self.data["interpretation"]
        self.assertEqual(x["wayback_delivery_proof"],"ABSENT")
        self.assertEqual(x["factor_vintage_content"],"RECOVERED")
        self.assertEqual(x["numerical_replay"],"PASS")


if __name__=="__main__":
    unittest.main()
