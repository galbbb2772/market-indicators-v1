# MASTER TOP V3 — Bubble Exhaustion V2.2 audit (2026-10-19)

**RESEARCH ONLY**. Not a true release-vintage PIT study, not independent OOS, not a calibrated crash probability. This branch does not change the main production system.

## Official availability evidence
FINRA Rule 4521 margin statistics are generally published in the **third week of the month after the reference month**, not at that reference month's close:
https://www.finra.org/rules-guidance/key-topics/margin-accounts/margin-statistics

The source archive contains no verified exact release dates for every month. The release documentary evidence in FINRA_RELEASE_EVIDENCE.csv gives dates by which figures were public, NOT exact initial timestamps. Therefore the +15/+25/+35/+45 calendar-day release models are **sensitivity scenarios**, not PIT reconstructions. Do not use September 2026 official balance to reconstruct any signal dated before the September balance's known release.

## Critical event timing results
Source: `v22_event_peak_timing_audit.csv`.
- 2000 peak 2000-03-24: ARMED **24 days early**, confirmation **98 days late**.
- 2007 peak 2007-10-09: ARMED **162 days early**, confirmation **234 days late**.
- 2018 Q4 approximately -20% drawdown: **missed** by Bubble Exhaustion.
- 2020 COVID approximately -34% drawdown: **missed**.
- 2022 peak 2022-01-03: ARMED **339 days early**, confirmation 125 days early.
- 2025 peak 2025-02-19: ARMED **40 days late**; confirmation 70 days late (after the trough).
Peak dates used as external reference, not independently selected event labels.

## Overlapping monthly windows — risk cohort findings
Source: `v22_monthly_forward_outcomes.csv` and corrected `v22_monthly_state_risk_summary.csv`. Out of 309 fully matured 12m month-end windows using **raw SPY daily close**. "20% fall" means peak-to-trough within the future window, not loss from signal day's entry. The same market collapse impacts many overlapping windows, so rates are NOT independent probabilities.

| Group | Through 2018 severe-window share (N) | 2019+ severe-window share (N) |
|---|---:|---:|
| IDLE | 8.2% (183) | 24.5% (49) |
| ARMED | 76.5% (17) | 25.0% (8) |
| ROLLOVER_ACTIVE | 100.0% (27) | 36.4% (22) |
| CAPE>=90 percentile | 28.8% (153) | 27.8% (79) |

This is **negative evidence against extrapolating earlier effectiveness**. The retrospective post-2019 ARMED frequency of >=20% next-year drawdowns (25.0%) is roughly equal to IDLE (24.5%), not evidence for a useful independent early top trigger. 2019+ is NOT untouched OOS, since 2021 and 2025 already affected earlier model design.

## 2026 status and controls
- Last completed monthly result **2026-09: ARMED_REHEATED**, Bubble Build 97.57, leverage rollover 7.08, current exhaustion confirmation **FALSE**.
- The episode began 2025-03, was confirmed 2025-04 and reheated by 2025-08. `ever_confirmed_in_episode` is not `current_confirmation`.
- October 2026 snapshots before month-end are PROVISIONAL and cannot trigger authoritative monthly states. Oct16 third-party SPY source has inconsistent OHLC and is excluded pending verification.
- False positives/misses must remain published; never tune thresholds by observed returns without resetting the declared study.

## Prospective OOS registration
Freeze this candidate as of **2026-10-19**; prospective first eligible *completed month* may be October 2026 conditional on actual availability proof, validated SPY close and prior-month CAPE. Capture source URL, content blob SHA, release/observation timestamps and input row cutoff before scoring. Declare future 6/12/18 month outcome windows and whether alert precedes price peak. No validation label until outcome window has completed. This is the only path to *future* independent evidence for these post-hoc rules.

Source mirrors (revised, unofficial): FINRA margin https://github.com/oid87/PersonalFiance/blob/main/data/margin_global_us.json ; Shiller CAPE https://github.com/adambnash-afk/shiller-data/blob/main/data/stock_market_data.json ; SPY https://github.com/oid87/PersonalFiance/blob/main/data/SPY.json .
