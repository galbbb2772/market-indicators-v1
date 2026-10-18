from __future__ import annotations

import unittest

from audit_ff_monthly_archive_probe import archive_url, CANDIDATES


class FFMonthlyArchiveProbeTests(unittest.TestCase):
    def test_url_shape_matches_known_archive_convention(self):
        self.assertEqual(
            archive_url(2022, 8),
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202022%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip",
        )

    def test_probe_contains_pre_cutoff_months_and_positive_control(self):
        self.assertIn((2021, 12), CANDIDATES)
        self.assertIn((2022, 1), CANDIDATES)
        self.assertIn((2022, 8), CANDIDATES)


if __name__ == "__main__":
    unittest.main()
