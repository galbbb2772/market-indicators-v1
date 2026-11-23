from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "policyshock_2022_primary_source_pit_audit.json"


class PolicyShock2022PrimarySourceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_primary_source_chain_passes(self):
        self.assertEqual(
            self.data["status"],
            "PASS_PRIMARY_SOURCE_PIT_CHAIN",
        )
        self.assertTrue(
            self.data["evidence"]["github_actions_live_download_passed"]
        )

    def test_h41_values_are_dated_official_release_evidence(self):
        self.assertEqual(
            [x["total_assets_millions"] for x in self.data["h41"]],
            [8078544.0, 8447981.0, 8757460.0],
        )
        self.assertTrue(
            all(
                x["evidence_level"] == "DATED_OFFICIAL_RELEASE_PAGE"
                for x in self.data["h41"]
            )
        )

    def test_frozen_policyshock_is_reproduced(self):
        self.assertAlmostEqual(
            self.data["policy_shock"],
            74.38861925775049,
            places=10,
        )

    def test_conservative_route_b_still_passes(self):
        x = self.data["conservative_route_b_check"]
        self.assertTrue(x["passes"])
        self.assertGreater(x["route_b"], x["threshold"])
        self.assertGreater(x["policy_margin_above_critical"], 0)

    def test_treasury_provenance_is_not_overclaimed(self):
        self.assertEqual(
            self.data["treasury"]["evidence_level"],
            "OFFICIAL_HISTORICAL_SERIES_NOT_ARCHIVED_JAN3_BYTES",
        )


if __name__ == "__main__":
    unittest.main()
