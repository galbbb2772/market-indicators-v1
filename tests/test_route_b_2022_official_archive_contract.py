from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_official_archive_audit.json"


class RouteB2022OfficialArchiveContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_official_archive_preserves_route_b_pass(self):
        self.assertTrue(self.data["passes"])
        self.assertGreater(self.data["route_b"], self.data["threshold"])

    def test_official_archive_size_stays_above_failure_boundary(self):
        self.assertGreater(
            self.data["size_weakness"],
            self.data["critical_size_weakness"],
        )

    def test_live_download_evidence_exists(self):
        self.assertTrue(
            self.data["evidence"]["github_actions_live_download_passed"]
        )

    def test_exact_jan3_vintage_is_not_overclaimed(self):
        self.assertFalse(self.data["exact_2022_01_03_vintage"])


if __name__ == "__main__":
    unittest.main()
