from __future__ import annotations

import unittest

from audit_policyshock_20220103_primary_sources import (
    H41_RELEASES,
    RATE_ANCHOR_TARGET,
    STRICT_LAG_LATEST,
    normalize_text,
    parse_treasury_2y_csv,
)


class PolicyShock2022PrimarySourceAuditTests(unittest.TestCase):
    def test_frozen_rate_dates(self):
        self.assertEqual(STRICT_LAG_LATEST.date().isoformat(), "2021-12-31")
        self.assertEqual(RATE_ANCHOR_TARGET.date().isoformat(), "2021-06-30")

    def test_treasury_parser_uses_2y_column(self):
        text = (
            "Date,1 Mo,3 Mo,6 Mo,1 Yr,2 Yr,3 Yr\n"
            "12/31/2021,0.06,0.05,0.19,0.39,0.73,0.97\n"
            "06/30/2021,0.05,0.05,0.06,0.07,0.25,0.46\n"
        )
        s = parse_treasury_2y_csv(text)
        self.assertEqual(float(s.loc["2021-12-31"]), 0.73)
        self.assertEqual(float(s.loc["2021-06-30"]), 0.25)

    def test_h41_frozen_observation_spacing(self):
        obs = [x["observation_date"] for x in H41_RELEASES]
        self.assertEqual(obs, ["2021-06-30", "2021-09-29", "2021-12-29"])

    def test_html_normalizer_keeps_visible_numbers(self):
        x = normalize_text("<html><td>Total assets</td><td>8,757,460</td></html>")
        self.assertIn("Total assets", x)
        self.assertIn("8,757,460", x)

    def test_html_normalizer_collapses_table_spacing(self):
        x = normalize_text("<tr><td>Total   assets</td><td>8,757,460</td></tr>")
        self.assertEqual(x, "Total assets 8,757,460")

    def test_preformatted_h41_visible_line_shape(self):
        from bs4 import BeautifulSoup
        import re

        html = "<pre>Other assets  31,827\nTotal assets  (0)  8,078,544  - 23,401</pre>"
        soup = BeautifulSoup(html, "html.parser")
        lines = [
            re.sub(r"\\s+", " ", line).strip()
            for line in soup.get_text("\\n").splitlines()
        ]
        self.assertIn("Total assets (0) 8,078,544 - 23,401", lines)


if __name__ == "__main__":
    unittest.main()
