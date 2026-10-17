from __future__ import annotations

import unittest

import pandas as pd

from update_market_top_shadow import (
    _prior_policy_state,
    compute_policy,
    compute_price,
    compute_size_weakness,
    compute_valuation,
    parse_fed_assets_mirror,
    parse_treasury_2y_csv,
    validate_source_freshness,
    walcl_actionable_eod_date,
)


class MarketTopForwardShadowTests(unittest.TestCase):
    def test_valuation_excludes_unfinished_current_month(self):
        shiller = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    ["2026-07-01", "2026-08-01", "2026-09-01", "2026-10-01"]
                ),
                "cape": [30.0, 35.0, 40.0, 80.0],
            }
        )
        x = compute_valuation(shiller, asof=pd.Timestamp("2026-10-16"))
        self.assertEqual(x["signal_month"], "2026-09")
        self.assertEqual(x["cape"], 40.0)
        self.assertEqual(x["score"], 100.0)

    def test_size_weakness_uses_latest_published_completed_factor_month(self):
        ff = pd.DataFrame(
            {
                "date": pd.to_datetime(
                    [
                        "2026-01-01",
                        "2026-02-01",
                        "2026-03-01",
                        "2026-04-01",
                        "2026-05-01",
                        "2026-06-01",
                        "2026-07-01",
                        "2026-08-01",
                    ]
                ),
                "smb": [-1.0, -1.0, -1.0, -1.0, -1.0, -1.0, 1.0, 1.0],
            }
        )
        x = compute_size_weakness(ff, asof=pd.Timestamp("2026-10-16"))
        self.assertEqual(x["factor_month"], "2026-08")
        self.assertIsInstance(x["score"], float)

    def test_treasury_2y_csv_parser(self):
        text = (
            "Date,1 Mo,3 Mo,6 Mo,1 Yr,2 Yr,3 Yr,5 Yr,7 Yr,10 Yr,20 Yr,30 Yr\n"
            "10/15/2026,4.60,4.65,4.70,4.75,4.77,4.70,4.60,4.55,4.50,4.80,4.90\n"
            "04/15/2026,3.60,3.65,3.70,3.72,3.76,3.80,3.90,4.00,4.10,4.50,4.60\n"
        )
        s = parse_treasury_2y_csv(text)
        self.assertEqual(s.index[-1], pd.Timestamp("2026-10-15"))
        self.assertEqual(float(s.iloc[-1]), 4.77)
        self.assertEqual(float(s.loc[pd.Timestamp("2026-04-15")]), 3.76)

    def test_fed_assets_static_mirror_parser(self):
        obj = {
            "generated_at_utc": "2026-10-17T01:23:07Z",
            "observations": [
                {
                    "date": (pd.Timestamp("2024-01-03") + pd.Timedelta(weeks=i)).date().isoformat(),
                    "value": 6_000_000 + i,
                }
                for i in range(120)
            ],
        }
        s = parse_fed_assets_mirror(obj)
        self.assertEqual(len(s), 120)
        self.assertEqual(s.attrs["mirror_generated_at_utc"], "2026-10-17T01:23:07Z")
        self.assertIn("static GitHub mirror", s.attrs["source"])

    def test_freshness_contract_accepts_current_fixture(self):
        out = validate_source_freshness(
            generated_at=pd.Timestamp(
                "2026-10-17T06:24:27Z"
            ).to_pydatetime(),
            market_asof=pd.Timestamp("2026-10-16"),
            policy={
                "dgs2_latest_date": "2026-10-16",
                "walcl_latest_date": "2026-10-14",
            },
            valuation={"signal_month": "2026-09"},
            size_weakness={"factor_month": "2026-08"},
        )
        self.assertEqual(out["status"], "PASS")
        self.assertEqual(out["market_lag_days"], 1)
        self.assertEqual(out["dgs2_lag_days"], 0)
        self.assertEqual(out["walcl_lag_days"], 2)
        self.assertEqual(out["ff_factor_lag_months"], 2)

    def test_freshness_contract_rejects_stale_daily_and_weekly_inputs(self):
        with self.assertRaisesRegex(ValueError, "DGS2 freshness"):
            validate_source_freshness(
                generated_at=pd.Timestamp("2026-10-17T06:24:27Z").to_pydatetime(),
                market_asof=pd.Timestamp("2026-10-16"),
                policy={
                    "dgs2_latest_date": "2026-10-01",
                    "walcl_latest_date": "2026-10-14",
                },
                valuation={"signal_month": "2026-09"},
                size_weakness={"factor_month": "2026-08"},
            )

        with self.assertRaisesRegex(ValueError, "WALCL freshness"):
            validate_source_freshness(
                generated_at=pd.Timestamp("2026-10-17T06:24:27Z").to_pydatetime(),
                market_asof=pd.Timestamp("2026-10-16"),
                policy={
                    "dgs2_latest_date": "2026-10-16",
                    "walcl_latest_date": "2026-09-20",
                },
                valuation={"signal_month": "2026-09"},
                size_weakness={"factor_month": "2026-08"},
            )

    def test_freshness_contract_rejects_stale_monthly_inputs(self):
        with self.assertRaisesRegex(ValueError, "CAPE freshness"):
            validate_source_freshness(
                generated_at=pd.Timestamp("2026-10-17T06:24:27Z").to_pydatetime(),
                market_asof=pd.Timestamp("2026-10-16"),
                policy={
                    "dgs2_latest_date": "2026-10-16",
                    "walcl_latest_date": "2026-10-14",
                },
                valuation={"signal_month": "2026-08"},
                size_weakness={"factor_month": "2026-08"},
            )

        with self.assertRaisesRegex(ValueError, "Fama-French freshness"):
            validate_source_freshness(
                generated_at=pd.Timestamp("2026-10-17T06:24:27Z").to_pydatetime(),
                market_asof=pd.Timestamp("2026-10-16"),
                policy={
                    "dgs2_latest_date": "2026-10-16",
                    "walcl_latest_date": "2026-10-14",
                },
                valuation={"signal_month": "2026-09"},
                size_weakness={"factor_month": "2026-06"},
            )

    def test_freshness_contract_rejects_stale_market_snapshot(self):
        with self.assertRaisesRegex(ValueError, "market as-of freshness"):
            validate_source_freshness(
                generated_at=pd.Timestamp("2026-10-17T06:24:27Z").to_pydatetime(),
                market_asof=pd.Timestamp("2026-10-01"),
                policy={
                    "dgs2_latest_date": "2026-10-01",
                    "walcl_latest_date": "2026-09-30",
                },
                valuation={"signal_month": "2026-09"},
                size_weakness={"factor_month": "2026-08"},
            )

    def test_walcl_normal_week_is_not_actionable_at_thursday_close(self):
        obs = pd.Timestamp("2026-10-14")  # Wednesday
        self.assertEqual(
            walcl_actionable_eod_date(obs),
            pd.Timestamp("2026-10-16"),   # Friday EOD
        )

    def test_walcl_thanksgiving_release_shift_is_not_actionable_friday(self):
        obs = pd.Timestamp("2026-11-25")  # Wednesday before Thanksgiving
        self.assertEqual(
            walcl_actionable_eod_date(obs),
            pd.Timestamp("2026-11-30"),   # Monday after Friday 4:30 release
        )

    def test_current_policy_fingerprint(self):
        dgs2 = pd.Series(
            [3.76, 4.77],
            index=pd.to_datetime(["2026-04-15", "2026-10-15"]),
        )
        walcl = pd.Series(
            [6705696.0, 6743028.0, 6755639.0],
            index=pd.to_datetime(["2026-04-15", "2026-07-15", "2026-10-14"]),
        )
        x = compute_policy(dgs2, walcl, asof=pd.Timestamp("2026-10-16"))
        self.assertAlmostEqual(x["rate_shock"], 100.0, places=10)
        self.assertAlmostEqual(x["taper_shock"], 6.860616780107296, places=8)
        self.assertAlmostEqual(x["policy_shock"], 62.744246712042916, places=8)
        self.assertEqual(x["walcl_latest_date"], "2026-10-14")

    def test_24m_high_is_calendar_based(self):
        idx = pd.bdate_range("2024-01-02", "2026-10-16")
        spy = pd.Series(150.0, index=idx)
        # This very old high is outside the trailing 24 calendar months.
        old = idx[idx <= pd.Timestamp("2024-08-15")][-1]
        spy.loc[old] = 999.0
        recent = idx[idx <= pd.Timestamp("2026-09-15")][-1]
        spy.loc[recent] = 200.0
        spy.iloc[-1] = 195.0

        x = compute_price(spy)
        self.assertEqual(x["high24_close"], 200.0)
        self.assertEqual(x["high24_date"], recent.date().isoformat())
        self.assertTrue(x["within_5pct_of_24m_high"])
        self.assertTrue(x["high_formed_within_3m"])
        self.assertTrue(x["top_location_gate"])

    def test_arm_clock_is_not_renewed_by_daily_armed_rows(self):
        history = [
            {
                "asof": "2026-01-03",
                "policy_path_state": "ARMED",
                "armed_at": "2026-01-03",
            },
            {
                "asof": "2026-02-03",
                "policy_path_state": "ARMED",
                "armed_at": "2026-01-03",
            },
            {
                "asof": "2026-03-03",
                "policy_path_state": "ARMED",
                "armed_at": "2026-01-03",
            },
        ]
        active = _prior_policy_state(history, asof=pd.Timestamp("2026-07-03"))
        self.assertEqual(active["state"], "ARMED")
        self.assertEqual(active["armed_at"], "2026-01-03")

        expired = _prior_policy_state(history, asof=pd.Timestamp("2026-07-04"))
        self.assertEqual(expired["state"], "IDLE")
        self.assertIsNone(expired["armed_at"])

    def test_triggered_state_is_terminal_like_frozen_replay(self):
        history = [
            {
                "asof": "2022-01-03",
                "policy_path_state": "ARMED",
                "armed_at": "2022-01-03",
            },
            {
                "asof": "2022-01-20",
                "policy_path_state": "TRIGGERED",
                "armed_at": "2022-01-03",
                "triggered_at": "2022-01-20",
            },
        ]
        x = _prior_policy_state(history, asof=pd.Timestamp("2022-02-01"))
        self.assertEqual(x["state"], "TRIGGERED")
        self.assertEqual(x["armed_at"], "2022-01-03")
        self.assertEqual(x["triggered_at"], "2022-01-20")


if __name__ == "__main__":
    unittest.main()
