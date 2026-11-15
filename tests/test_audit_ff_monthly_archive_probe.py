from __future__ import annotations

import unittest

from audit_ff_monthly_archive_probe import archive_url, CANDIDATES, run_probe


class FFMonthlyArchiveProbeTests(unittest.TestCase):
    def test_url_shape_matches_known_archive_convention(self):
        self.assertEqual(
            archive_url(2022, 8),
            "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
            "Data_Library/Historical_Archives/08%202022%20Update/ftp/"
            "F-F_Research_Data_Factors_CSV.zip",
        )

    def test_probe_contains_period_labeled_candidates_and_positive_control(self):
        self.assertIn((2021, 12), CANDIDATES)
        self.assertIn((2022, 1), CANDIDATES)
        self.assertIn((2022, 8), CANDIDATES)

    def test_present_day_directory_probe_cannot_claim_publication_time(self):
        from unittest.mock import patch

        def fake_probe(y, m):
            from audit_ff_monthly_archive_probe import Probe
            last = {
                (2021,10): "202109",
                (2021,11): None,
                (2021,12): "202111",
                (2022,1): "202112",
                (2022,2): "202201",
                (2022,8): "202207",
            }[(y,m)]
            valid = last is not None
            return Probe(
                y,m,archive_url(y,m),
                200 if valid else 404,
                "application/zip" if valid else "text/html",
                100000 if valid else 0,
                valid,last,
                bool(last and last >= "202111"),
                None,
            )

        with patch("audit_ff_monthly_archive_probe.probe_one", side_effect=fake_probe):
            x=run_probe()
        self.assertEqual(
            x["schema_version"],
            "ff-monthly-official-archive-probe-2",
        )
        self.assertTrue(x["dec2021_labeled_archive_exists_now"])
        self.assertFalse(x["publication_time_pre_cutoff_proven"])
        self.assertNotIn(
            "pre_cutoff_official_snapshot_with_202111_found",
            x,
        )


if __name__ == "__main__":
    unittest.main()
