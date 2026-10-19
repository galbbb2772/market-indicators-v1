from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_ff_publication_page_wayback_evidence.json"


class FFPublicationPageEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_publication_page_proof_remains_absent(self):
        self.assertEqual(
            self.data["status"],
            "NO_PRE_CUTOFF_PUBLICATION_PAGE_PROOF",
        )
        self.assertFalse(
            self.data["publication_time_202111_independently_proven"]
        )
        self.assertEqual(self.data["query_errors"], [])

    def test_strongest_parseable_page_only_reaches_october_2021(self):
        x = self.data["strongest_parseable_pre_cutoff_page"]
        self.assertEqual(x["monthly_returns_terminal_ym"], "202110")

    def test_numerical_replay_remains_pass(self):
        x = self.data["established_independently"]
        self.assertEqual(x["official_dec2021_factor_vintage_content"], "RECOVERED")
        self.assertEqual(x["numerical_size_weakness_replay"], "REPRODUCIBLE")
        self.assertEqual(x["conservative_route_b"], "PASS")
        self.assertGreater(x["route_b"], 85)


if __name__ == "__main__":
    unittest.main()
