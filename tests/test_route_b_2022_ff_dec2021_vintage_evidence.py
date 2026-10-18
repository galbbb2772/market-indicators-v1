from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_ff_dec2021_vintage_evidence.json"


class RouteB2022FFDec2021VintageEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_official_dec2021_vintage_content_is_recovered(self):
        x = self.data
        self.assertEqual(
            x["evidence_interpretation"]["factor_vintage_content"],
            "RECOVERED_OFFICIAL_DEC2021_VINTAGE",
        )
        self.assertEqual(x["source"]["last_month"], "202111")
        self.assertIn("202111 CRSP database", x["source"]["internal_header"])

    def test_frozen_route_b_still_passes(self):
        x = self.data["frozen_replay"]
        self.assertTrue(x["passes"])
        self.assertGreater(x["route_b"], x["threshold"])
        self.assertGreater(x["size_margin_above_critical"], 0)

    def test_web_delivery_provenance_is_not_overclaimed(self):
        self.assertEqual(
            self.data["evidence_interpretation"]["publication_time_bytes"],
            "NOT_PROVEN_BY_HTTP_METADATA_OR_WAYBACK",
        )
        self.assertEqual(len(self.data["source"]["zip_sha256"]), 64)


if __name__ == "__main__":
    unittest.main()
