from __future__ import annotations

import unittest
from unittest.mock import patch

from audit_ff_dec2021_wayback_namespace import (
    CUTOFF,
    PREFIXES,
    _is_target_namespace,
    _query_prefix,
    run,
)


class FFDec2021NamespaceWaybackTests(unittest.TestCase):
    def test_cutoff_and_namespace_prefixes_are_frozen(self):
        self.assertEqual(CUTOFF, "20220103235959")
        self.assertGreaterEqual(len(PREFIXES), 2)
        self.assertTrue(all("12%202021%20Update" in x for x in PREFIXES))

    def test_namespace_match_accepts_encoded_or_decoded_target(self):
        self.assertTrue(
            _is_target_namespace(
                "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
                "Data_Library/Historical_Archives/12%202021%20Update/ftp/a.zip"
            )
        )
        self.assertFalse(
            _is_target_namespace(
                "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
                "Data_Library/Historical_Archives/08%202022%20Update/ftp/a.zip"
            )
        )

    def test_prefix_query_retries_one_transient_timeout(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return [["timestamp", "original"], ["20211201000000", "x"]]

        class Session:
            def __init__(self):
                self.calls = 0

            def get(self, *args, **kwargs):
                self.calls += 1
                if self.calls == 1:
                    raise TimeoutError("transient")
                return Response()

        s = Session()
        with patch("audit_ff_dec2021_wayback_namespace.time.sleep"):
            data, error = _query_prefix(
                s,
                PREFIXES[0],
                attempts=2,
                timeout=1,
            )
        self.assertIsNone(error)
        self.assertEqual(s.calls, 2)
        self.assertEqual(data[1][0], "20211201000000")

    def test_prefix_query_still_fails_closed_after_all_retries(self):
        class Session:
            def get(self, *args, **kwargs):
                raise TimeoutError("persistent")

        with patch("audit_ff_dec2021_wayback_namespace.time.sleep"):
            data, error = _query_prefix(
                Session(),
                PREFIXES[0],
                attempts=2,
                timeout=1,
            )
        self.assertIsNone(data)
        self.assertIn("persistent", error)

    def test_capture_is_delivery_evidence_but_empty_result_is_not_nonpublication(self):
        capture = {
            "timestamp": "20211230120000",
            "original": (
                "https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/"
                "Data_Library/Historical_Archives/12%202021%20Update/ftp/x.zip"
            ),
            "digest": "ABC",
        }
        with patch(
            "audit_ff_dec2021_wayback_namespace.find_namespace_captures",
            return_value=([capture], []),
        ):
            x = run()
        self.assertEqual(
            x["status"],
            "PRE_CUTOFF_DEC2021_NAMESPACE_CAPTURE_FOUND",
        )
        self.assertTrue(x["namespace_pre_cutoff_delivery_evidence"])

        with patch(
            "audit_ff_dec2021_wayback_namespace.find_namespace_captures",
            return_value=([], []),
        ):
            y = run()
        self.assertEqual(
            y["status"],
            "NO_PRE_CUTOFF_DEC2021_NAMESPACE_CAPTURE",
        )
        self.assertFalse(y["namespace_pre_cutoff_delivery_evidence"])


if __name__ == "__main__":
    unittest.main()
