from __future__ import annotations

import unittest

from audit_ff_publication_page_wayback import extract_factor_page_evidence


class FFPublicationPageWaybackTests(unittest.TestCase):
    def test_detects_november_2021_terminal_month(self):
        html = """
        <html><body>
        <h1>Description of Fama/French Factors</h1>
        <div>Monthly Returns: July 1926 - November 2021</div>
        <div>SMB Small Minus Big</div>
        <div>HML High Minus Low</div>
        </body></html>
        """
        x = extract_factor_page_evidence(html)
        self.assertTrue(x["has_factor_identity"])
        self.assertTrue(x["target_202111_publication_visible"])
        self.assertEqual(x["monthly_returns_terminal"], "November 2021")
        self.assertEqual(x["monthly_returns_terminal_ym"], "202111")

    def test_october_2021_does_not_prove_target(self):
        html = """
        Description of Fama/French Factors
        Monthly Returns: July 1926 - October 2021
        SMB HML
        """
        x = extract_factor_page_evidence(html)
        self.assertTrue(x["has_factor_identity"])
        self.assertFalse(x["target_202111_publication_visible"])
        self.assertEqual(x["monthly_returns_terminal"], "October 2021")
        self.assertEqual(x["monthly_returns_terminal_ym"], "202110")

    def test_december_2021_terminal_also_proves_target_available(self):
        html = """
        Description of Fama/French Factors
        Monthly Returns: July 1926 - December 2021
        SMB HML
        """
        x = extract_factor_page_evidence(html)
        self.assertTrue(x["target_202111_publication_visible"])
        self.assertEqual(x["monthly_returns_terminal_ym"], "202112")

    def test_unrelated_november_text_does_not_pass(self):
        html = """
        Description of Fama/French Factors
        Monthly Returns: July 1926 - October 2021
        News updated November 2021.
        SMB HML
        """
        x = extract_factor_page_evidence(html)
        self.assertFalse(x["target_202111_publication_visible"])


if __name__ == "__main__":
    unittest.main()
