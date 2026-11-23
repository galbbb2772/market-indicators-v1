from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "route_b_2022_ff_dec2021_namespace_wayback_evidence.json"


class FFDec2021NamespaceEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.x = json.loads(PATH.read_text(encoding="utf-8"))

    def test_namespace_capture_is_absent_without_query_errors(self):
        self.assertEqual(
            self.x["status"],
            "NO_PRE_CUTOFF_DEC2021_NAMESPACE_CAPTURE",
        )
        self.assertEqual(self.x["query_errors"], [])
        self.assertEqual(self.x["capture_count"], 0)
        self.assertFalse(
            self.x["namespace_pre_cutoff_delivery_evidence"]
        )

    def test_absence_is_not_misrepresented_as_nonpublication(self):
        self.assertIn(
            "does not prove",
            self.x["interpretation"]["not_proven"].lower(),
        )
        self.assertEqual(
            self.x["interpretation"]["delivery_status"],
            "ARCHIVE_COVERAGE_GAP_REMAINS",
        )


if __name__ == "__main__":
    unittest.main()
