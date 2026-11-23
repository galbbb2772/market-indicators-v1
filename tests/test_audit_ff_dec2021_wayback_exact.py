from __future__ import annotations

import unittest

from audit_ff_dec2021_wayback_exact import CUTOFF, TARGET_MONTH, TARGET_SHA256, URLS


class FFDec2021WaybackExactTests(unittest.TestCase):
    def test_cutoff_and_target(self):
        self.assertEqual(CUTOFF,"20220103235959")
        self.assertEqual(TARGET_MONTH,"202111")
        self.assertEqual(len(TARGET_SHA256),64)

    def test_exact_historical_archive_urls(self):
        self.assertEqual(len(URLS),2)
        self.assertTrue(all("Historical_Archives/12%202021%20Update/" in x for x in URLS))


if __name__=="__main__":
    unittest.main()
