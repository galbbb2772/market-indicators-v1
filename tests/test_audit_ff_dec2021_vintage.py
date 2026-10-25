from __future__ import annotations

import unittest

from audit_ff_dec2021_vintage import TARGET_MONTH, URL


class FFDec2021VintageAuditTests(unittest.TestCase):
    def test_target_is_november_2021(self):
        self.assertEqual(TARGET_MONTH, "202111")

    def test_url_is_official_december_2021_archive(self):
        self.assertIn("Historical_Archives/12%202021%20Update/", URL)
        self.assertTrue(URL.endswith("F-F_Research_Data_Factors_CSV.zip"))


if __name__ == "__main__":
    unittest.main()
