# MASTER TOP V3 / Bubble Exhaustion — V2.1 lifecycle correction (research)

**2026-10-19 | NOT PRODUCTION | not point-in-time-vintage / not OOS**

## Data findings
- V2 was holding **CONFIRMED** as a latched state from 2025-04 all the way into 2026 despite leverage re-heating. Treating that as a fresh live confirmation would be wrong.
- V2.1 keeps the *bubble episode* alive separately from the *current confirmation*. After rollover <=10 points in two successive valid months, confirmation is deactivated and the episode is downgraded to **ARMED_REHEATED**. A later >=20 point rollover can issue **RECONFIRM** within the same episode; no new episode ID.
- True **RESET** still requires both vulnerability Build <=65 and leverage Memory <=70 for three consecutive eligible monthly observations. No fixed 12-month cooldown.
- First ARM needs two valid consecutive months at Build>=85, Memory>=80, CAPE-percentile>=85 and SPY top ratio>=0.90. These thresholds are EXPLORATORY and selected with knowledge of historical outcomes; no OOS claim.

## Historical periods (assumed margin availability = month-end +25 calendar days)
- 2000-02: ARM; confirmed 2000-06; reheat downgrades 2001-12; reset 2002-01; 12m after ARM min-vs-entry -9.81%, peak-to-trough drawdown -19.28%.
- 2007-04: ARM; confirmed 2008-05; reheat downgrades none; reset 2009-02; 12m after ARM min-vs-entry -13.68%, peak-to-trough drawdown -18.20%.
- 2021-01: ARM; confirmed 2021-08; reheat downgrades none; reset 2023-02; 12m after ARM min-vs-entry 1.66%, peak-to-trough drawdown -9.73%.
- 2025-03: ARM; confirmed 2025-04; reheat downgrades 2025-08; reset not yet; 12m after ARM min-vs-entry -11.25%, peak-to-trough drawdown -12.05%.

## Current proxy state
- 2026-09 last COMPLETED scoring month: **ARMED_REHEATED**, active confirmation=false, continuous episode originated 2025-03.
- 2026-10 data read as of **2026-10-15** is PARTIAL MONTH, not a finalized October monthly signal. It remains ARMED_REHEATED. The 2026-10-16 SPY bar was excluded because its reported open was 773.24 against a 773.23 high, and volume was only 6.6 million, pointing to an incomplete / noisy market snapshot.
- CAPE is reconstructed from a third-party Shiller mirror, and FINRA margin statistics from another third-party mirror; the +25d release delay is not official historic release-vintage confirmation.
- This is a **risk regime classification**, not a percentage likelihood of an impending crash.

## Known weaknesses
- **2007 rollover confirmation occurs only in May 2008**, severely delayed for peak-timing.
- Only four overlapping crash/regime episodes; conditional hit-rates have huge sampling uncertainty.
- The 2025 cycle demonstrates why persistent state ≠ persistent current rollover confirmation.
- Proper prospective OOS, external data-source replication, actual FINRA release calendar, and pricing-bar sanity checks remain mandatory.
