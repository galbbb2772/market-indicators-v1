from __future__ import annotations

import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/"docs"/"index.html").read_text(encoding="utf-8")

class NG3DashboardContractTests(unittest.TestCase):
    def test_ng3_is_labeled_prospective_research(self):
        self.assertIn("Route_A NG3 · Prospective Monitor",HTML)
        self.assertIn("第一可计入验证的 effective month 固定为 <b>2026-12</b>",HTML)
        self.assertIn("不是 legacy Route_A，也不进入 Market Model V2",HTML)

    def test_dashboard_reads_research_snapshot(self):
        self.assertIn("./data/market_top_ng3_current.json",HTML)
        self.assertIn("./data/market_top_ng3_episodes.json",HTML)
        self.assertIn("renderNG3",HTML)
        self.assertIn("renderNG3Episodes",HTML)

    def test_episode_ledger_never_implies_automatic_promotion(self):
        self.assertIn("review eligible",HTML)
        self.assertIn("automatic promotion",HTML)

    def test_nonprospective_snapshot_is_explicitly_diagnostic(self):
        self.assertIn("RETROSPECTIVE_TRAINING_DIAGNOSTIC",HTML)
        self.assertIn("不计入 NG3 prospective validation",HTML)
        self.assertIn("任何参数改动必须升级为 NG4",HTML)

if __name__=="__main__":
    unittest.main()
