# MASTER TOP V3 — Bubble Exhaustion V2.3 Robustness Audit

**Study date:** 2026-10-19  
**Status:** retrospective diagnostic only — NOT verified OOS; NOT vintage-perfect point-in-time (PIT); NOT a calibrated drawdown probability; DO NOT merge into production.

## Why V2.3 exists

The V2.2 study had 309 overlapping 12-month forward drawdown windows. The same bear market is therefore counted many times. V2.3 uses annual anchor months (Jan, Apr, Jul, Oct) to obtain approximately nonoverlapping forward 12-month windows *within each anchor*. The four anchors are highly correlated replicas of the SAME history; do not pool them as independent samples.

### Outcome and source
- Severe outcome: peak-to-trough max drawdown of at least 20% within the **future** 365 calendar-day horizon after a month-end signal, calculated using unadjusted daily SPY closes in V2.2.
- Separate robustness target: loss of at least 20% from the **signal-date price** to a subsequent price minimum within 365 days.
- Published in inherited `research/master_top_v3_be_v2/v22_monthly_forward_outcomes.csv`. State mapping uses V2.1 reheating/reset lifecycle `state_v21_reheat_lifecycle.csv`.
- `BUILD` = prior V2.1 Bubble Build numerical research score (0–100); `CAPE` = expanding historical percentile of Shiller CAPE.
- Scores use retrospectively reconstructed data and a *hypothetical* FINRA release lag. No score series is fully PIT-verified.

## Annual anchor AUC — all usable years (2000–2025, 25–26 annual observations)

| Month | N | AUC: Build | AUC: CAPE | AUC: Rollover | Delta Build − CAPE |
|---|---:|---:|---:|---:|---:|
| Jan | 26 | .481 | .684 | .711 | -.203 |
| Apr | 26 | .617 | .750 | .567 | -.133 |
| Jul | 26 | .752 | .827 | .598 | -.075 |
| Oct | 25 | .702 | .737 | .614 | -.035 |

**Result:** Build did not outperform plain CAPE under any of the four full-history annual-anchor AUC comparisons. This is *no evidence of incremental forecast utility*; not proof that Build is inferior.

### Paired resampling uncertainty

Resample annual observations with replacement, separately for each annual anchor (2,500 deterministic draws; exclude bootstrap samples with only one outcome class). Estimated 2.5–97.5% intervals for AUC(Build)−AUC(CAPE):

| Anchor | Bootstrap interval |
|---|---|
| January | [-.608, +.182] |
| April | [-.533, +.261] |
| July | [-.451, +.305] |
| October | [-.456, +.417] |

All include zero. Simple annual resampling is an *approximate stability diagnostic*, not an exact IID confidence interval: adjacent annual windows may share shock regimes; there are very few distinct bubbles. The four anchored analyses cannot be treated as independent replications.

## More recent history: 2019+ NOT OOS

Just 7 annual observations for Jan/Apr/Jul and 6 for Oct. ARMED at each Jan/Apr/Jul has only **one annual exposure** (0/1 severe-window events in Jan, 0/1 in Apr, 1/1 in Jul). October has none. State percentages are not statistically meaningful. 2019+ thresholds and architecture were already influenced by knowledge of 2021–2025, so the date split is not genuinely untouched OOS.

## Additional target definition

A future-window peak-to-trough fall is *not* the same as a 20% loss from the signal date: January has 7 severe future-window MDD events but only 5 signal-date-to-minimum >=20% cases across 26 observations. Corresponding annual counts: Apr (6 vs 5), Jul (7 vs 4), Oct (6 vs 6). Treat these as different scientific claims, not interchangeable risk probabilities.

## Decision

1. Retain two-state *descriptive* lifecycle, but **reject statistical validation / production freeze**.
2. Publish AUC and state counts alongside CAPE baseline and no-signal baseline.
3. No new optimizations to ARMED/CAPE/Rollover thresholds using post-2018 outcomes.
4. Require real FINRA publication timestamps and robust source snapshots before treating any retrospective row as PIT.
5. Prospectively log monthly signals only after full source availability; first prospective month cannot occur until required datasets actually release. Store code SHA, raw source blobs, known_at timestamps and revisions.
6. Bubble route cannot cover exogenous shock declines alone (2018 and pandemic 2020 were missed), so maintain separate Policy–Breadth/Shock route. Do not merge complementary signals until separately tested.
7. Next experiment: assess **whether rollover timing adds incremental information conditional on CAPE** under predeclared controls, matched to contemporaneous market level and excluding post-crash confirmation. No parameter fishing.

## Files

- `V23_ANNUAL_DISCRIMINATION.csv`: four annual offsets × three periods × dual target discrimination; approximate bootstrap intervals and valid replicate counts.
- `V23_ANNUAL_STATE_COUNTS.csv`: direct counts, no inflated percentages.
- `V23_POST2019_ANNUAL_OBSERVATIONS.csv`: all 27 post-2019 annual-anchor rows to allow hand audit; these observations are correlated across offsets.
- `analyze_v23.py`: standalone stdlib script to regenerate the annual audit from the two inherited V2.2 CSV inputs.

**Do not describe the reported conditional severe outcome proportions as forward crash probabilities.**
