from __future__ import annotations

import unittest

from audit_ff_wayback_202201 import CUTOFF, ORIGINAL_URLS


class FF2022WaybackAuditTests(unittest.TestCase):
    def test_cutoff_is_jan3_2022(self):
        self.assertEqual(CUTOFF, "20220103235959")

    def test_both_https_and_http_source_urls_are_queried(self):
        self.assertEqual(len(ORIGINAL_URLS), 2)
        self.assertTrue(any(x.startswith("https://") for x in ORIGINAL_URLS))
        self.assertTrue(any(x.startswith("http://") for x in ORIGINAL_URLS))


if __name__ == "__main__":
    unittest.main()
