# MASTER TOP V2.1.8 — full-date frozen policy + top two-gate audit

**Executed:** 2026-10-23 on real data. `RESEARCH_ONLY`; no official V2.1.8 historical score series was computed. No threshold has been changed.

## Primary evidence

- GitHub Actions **SUCCESS**: [full-date run 39919678256](https://github.com/galbbb2772/market-indicators-v1/actions/runs/39919678256).
- Artifact: `master-top-v218-historical-two-gate-full-dates`, **ID 12486257405**; includes **6,994 daily rows** `all_days.csv` and full `summary.json`.
- S&P 500 **^GSPC real Yahoo daily close**: 1990-01-02 — 2026-10-22.
- U.S. Treasury **2Y CMT public historical mirror** (`fujiapple852/yield` sourced from Treasury XML): 1990-01-02 — 2026-10-22. FRED official DGS2 public CSV did not respond within 12 seconds in GitHub Actions and was **not** quietly described as a successful FRED run.
- The alternate 2Y series was cross-checked with independently connected Massive U.S. Treasury yield data: 2006-06-29 = 5.21%, 2022-01-03 = 0.78%, 2026-10-21 = 4.81%.
- Actual source SHA-256 and per-row rate observation dates are pinned inside `summary.json`/`all_days.csv`. All input rate lookups strictly use observations on or before the target date; 1M and 6M are calendar offsets.
- **10 offline formula and data-source tests passed.** Historical source gate passed; no fabricated H/L.

## Exact logical distinction

V2.1.8 frozen:

```
Policy = sqrt(R1 * R6)
TopProx = clip((^GSPC_close / rolling_1260_day_high - .95)/.05, 0, 1)
HL >= 75 required
Route = Policy * sqrt(HL/100) * sqrt(TopProx)
Trigger if Route >= 55
```

Because `0 <= HL <= 100`, **maximum possible route** even under extreme H/L=100 is `Policy * sqrt(TopProx)` whenever the 95% top gate passes. Thus these conclusions **are rigorous mathematical impossibility bounds** conditional on price/rates data, not an imputed actual route score.

- `TOP_GATE_IMPOSSIBLE`: <95% of 60M ^GSPC high -> no score can trigger.
- `POLICY_UPPER_BOUND_IMPOSSIBLE`: even HL=100 falls below 55 -> cannot trigger.
- `CONDITIONALLY_POSSIBLE_IF_MISSING_HL_SUFFICIENT`: could trigger **only if** the not-yet-rebuilt real 20-session 52-week high/low breadth has sufficient value; this is NOT an observed alert.

## Full historical coverage: 1999-01-04 through 2026-10-22

| Mutually exclusive classification | Daily sessions | Share |
|---|---:|---:|
| Top gate makes trigger impossible | 3,748 | 53.6% |
| Policy × top upper bound makes trigger impossible | 2,900 | 41.5% |
| **Possible only conditional on missing true H/L** | **346** | **4.9%** |
| Missing Treasury source observations | 0 | 0% |
| **Total** | **6,994** | 100% |

The 346 are **NOT confirmed triggers** or episodes; they must not be counted as hit rate, false positives, or full-score observations. A single episode can include multiple candidate days.

## Important historical windows

| Historical window | All sessions | Conditionally possible (NOT an alert count) | Notes |
|---|---:|---:|---|
| 1999–2001 dot-com | 752 | 70 | 1999-03-10 through 2000-03-28; no statement of model detection without H/L |
| 2005–2006 negative control | 503 | 39 | 2006-02-16 through 2006-07-03; **2006-06-29 control itself impossible** by upper bound ~44.96 |
| 2007–2009 crisis | 756 | 8 | May–June 2007 only; missed periods cannot be assessed without real H/L and proper episode definitions |
| 2017 control | 251 | 51 | Potential false alarms MUST be tested against actual H/L, not assumed away |
| 2018 correction | 312 | 52 | Selected historical anchor Oct 05 possible, but **post-top** |
| 2019-10 to 2020-12 COVID | 317 | **0** | V2.1.8 policy/top route **could not** have triggered under this input history, even with HL=100 |
| 2021–2022 bear | 503 | 41 | 2021-10-21 through 2022-03-29; selected 2021-12-15 historical score is mathematically feasible |
| 2023 negative control | 250 | **0** | Both frozen gates together rule out all 250 sessions regardless of missing H/L |
| 2025 tariff correction | 250 | **0** | Bounded V2.1.8 cannot trigger under this two-factor history, not a statement about other models |
| 2026 prefreeze period | 199 | 68 | Existing seed episode cannot be claimed new OOS |
| 2026 postfreeze through 2026-10-22 | 4 | **0** | Upper-bound cannot trigger **new** signals in these sessions; this does not close an existing episode |

## Selected anchor crosschecks

| Date | Archived scored route | Real two-gate upper bound (HL=100) | Inference |
|---|---:|---:|---|
| 1999-11-29 | 76.90 | 81.15 | Mathematically feasible |
| **2006-06-29** | **44.40** | **44.96** | **Threshold55 impossible**, confirming the control's policy/top gate logic |
| 2018-10-05 | 66.06 | 74.39 | Mathematically feasible; post-top confirmation |
| 2021-12-15 | 69.42 | 75.37 | Mathematically feasible, not independently regenerated |
| 2026-09-10 | 60.88 seed | 68.44 | Pre-freeze seed remains non-prospective |
| 2026-10-09 | 99.33 seed | 99.05 | Proxy/price-source deviation; do not claim exact re-reproduction |
| 2026-10-22 | no confirmed V2.1.8 score | **0.00** | **Two-gate bound only**, not a production recommendation |

## Additional important source-definition gap

`main:master_top_v218.py` uses **closing-price-based** 252-session highs/lows (`close >= prior max(close)`) while the separately archived `master-top-v218-live-source` branch uses **intraday high/low** with strict breakout tests (`high > prior max(high)`, `low < prior min(low)`). The dated **2026-10-17 original frozen PR #8** confirms `CLOSE_252_INCLUSIVE_FROZEN` as the authentic production comparator, while the later intraday-price branch is a **distinct non-equivalent experiment**. It must not silently replace the original frozen model. Details in `MASTER_TOP_V218_FREEZE_INPUT_PARITY_2026_10_23.md`.

Until the 252-session *point-in-time stock universe* and original close-inclusive H/L methodology are restored, **full model recall, historical misfires, forward outcomes and per-crisis confusion matrices remain unknown**. No retrofitted substitute is allowed to count as the original frozen route.

## Evidence status

`REAL_FULL_DATE_POLICY_AND_TOP_REPLAY_VERIFIED;`
`FULL_BREADTH_AND_EPISODE_BACKTEST_BLOCKED_PIT_INPUT_DATA;`
`NO_NEW_V218_PRODUCTION_SCORE;`
`NO_FORMULA_RETUNING.`

Reproducibility: run the script, inspect the artifact; GitHub Actions remains research-only and does **not** overwrite `docs/data/master_top_v218.json` or publish live Dashboard values.
