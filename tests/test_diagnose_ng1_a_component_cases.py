from __future__ import annotations

import unittest

from diagnose_ng1_a_component_cases import TARGETS


class NG1ACaseComponentDiagnosticTests(unittest.TestCase):
    def test_frozen_effective_lags_are_explicit(self):
        self.assertEqual(TARGETS["1998-11"], {"ff":"199809","credit":"199810"})
        self.assertEqual(TARGETS["2007-11"], {"ff":"200709","credit":"200710"})
        self.assertEqual(TARGETS["2012-02"], {"ff":"201112","credit":"201201"})


if __name__=="__main__":
    unittest.main()
