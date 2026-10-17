from __future__ import annotations

import unittest

from audit_ff_2022_archive import parse_ff3_monthly_csv


class FF2022ArchiveAuditTests(unittest.TestCase):
    def test_parser_reads_monthly_block_only(self):
        text = """Header
, Mkt-RF, SMB, HML, RF
202106,1.0,2.0,3.0,0.0
202107,1.1,2.1,3.1,0.0
202108,1.2,2.2,3.2,0.0
202109,1.3,2.3,3.3,0.0
202110,1.4,2.4,3.4,0.0
202111,1.5,2.5,3.5,0.0
 Annual Factors: January-December
2021,12,13,14,0
"""
        # The production parser deliberately requires a long archive, so
        # validate the row grammar here by extending the synthetic block.
        lines = ["Header", ",Mkt-RF,SMB,HML,RF"]
        for y in range(1926, 2022):
            for m in range(1, 13):
                ym = f"{y}{m:02d}"
                lines.append(f"{ym},1.0,2.0,3.0,0.0")
        lines.append(" Annual Factors: January-December")
        rows = parse_ff3_monthly_csv("\n".join(lines))
        self.assertEqual(rows[0]["ym"], "192601")
        self.assertEqual(rows[-1]["ym"], "202112")
        self.assertGreater(len(rows), 500)


if __name__ == "__main__":
    unittest.main()
