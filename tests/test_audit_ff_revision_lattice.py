from __future__ import annotations

import unittest

from audit_ff_revision_lattice import ARCHIVES, build_lattice


class FFRevisionLatticeTests(unittest.TestCase):
    def test_expected_official_archive_cuts_are_frozen(self):
        self.assertEqual(
            [x["id"] for x in ARCHIVES],
            [
                "JULY_2022",
                "JULY_2023",
                "JULY_2024",
                "JULY_2025",
                "AUGUST_2026",
            ],
        )
        self.assertTrue(all("Historical_Archives" in x["url"] for x in ARCHIVES))

    def test_lattice_uses_worst_case_not_average(self):
        base_six = [
            {"ym": "202106", "smb": 1.0},
            {"ym": "202107", "smb": -1.0},
            {"ym": "202108", "smb": 0.0},
            {"ym": "202109", "smb": 0.0},
            {"ym": "202110", "smb": -1.0},
            {"ym": "202111", "smb": -1.0},
        ]
        rows = [
            {
                "id": "A",
                "size_weakness": 84.0,
                "route_b": 85.10,
                "passes": True,
                "smb_202106_to_202111": base_six,
            },
            {
                "id": "B",
                "size_weakness": 86.0,
                "route_b": 85.70,
                "passes": True,
                "smb_202106_to_202111": [
                    {**x, "smb": x["smb"] + 0.1}
                    for x in base_six
                ],
            },
        ]
        x = build_lattice(rows)
        self.assertTrue(x["all_archives_pass"])
        self.assertEqual(x["size_weakness"]["min"], 84.0)
        self.assertEqual(x["size_weakness"]["max"], 86.0)
        self.assertAlmostEqual(
            x["route_b"]["minimum_margin_above_threshold"],
            0.10,
            places=12,
        )

    def test_one_failed_archive_fails_entire_lattice(self):
        six = [
            {"ym": ym, "smb": 0.0}
            for ym in ["202106","202107","202108","202109","202110","202111"]
        ]
        x = build_lattice([
            {
                "id":"A","size_weakness":85.0,"route_b":85.2,
                "passes":True,"smb_202106_to_202111":six,
            },
            {
                "id":"B","size_weakness":80.0,"route_b":84.0,
                "passes":False,"smb_202106_to_202111":six,
            },
        ])
        self.assertFalse(x["all_archives_pass"])
        self.assertLess(x["route_b"]["minimum_margin_above_threshold"], 0.0)


if __name__ == "__main__":
    unittest.main()
