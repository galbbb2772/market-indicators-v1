from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "research" / "v24_legacy_early_breadth_provenance_gap.json"


class V24LegacyEarlyBreadthProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(PATH.read_text(encoding="utf-8"))

    def test_legacy_fixture_is_preserved_but_not_called_reproducible(self):
        x = self.data["accepted_fixture"]
        self.assertEqual(x["accepted_trigger_window"], "2021-10")
        self.assertEqual(x["accepted_trigger_type"], "EARLY_BREADTH")
        self.assertFalse(x["formula_reproducible"])
        self.assertFalse(x["code_artifact_recovered"])

    def test_replacements_cannot_define_original_formula(self):
        self.assertTrue(self.data["policy"]["preserve_legacy_fixture"])
        self.assertFalse(self.data["policy"]["may_use_fixture_as_formula_golden"])
        self.assertFalse(self.data["policy"]["may_claim_exact_reproduction"])
        self.assertFalse(self.data["policy"]["may_tune_replacement_to_fixture"])

    def test_all_screened_replacements_are_rejected(self):
        self.assertTrue(all(v == "REJECTED" for v in self.data["replacement_evidence"].values()))


if __name__ == "__main__":
    unittest.main()
