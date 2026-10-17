# MASTER TOP V2.1.8 — Frozen Supplemental Policy × Breadth Route

Freeze date: **2026-10-17**

This route supplements the existing MASTER TOP V2.1 baseline. It does not replace the old Formation / Vulnerability / engine-specific logic. If a baseline trigger is available, the combined trigger is `max(baseline_trigger, supplemental_route)`.

## Frozen formula

```text
R6 = 100 * clip((Δ2Y_6M - 10bp) / 60bp, 0, 1)
R1 = 100 * clip(Δ2Y_1M / 20bp, 0, 1)
Policy = sqrt(R6 * R1)

HL = 100 * sqrt(
    clip(-mean(HLBalance_20D) / 0.30, 0, 1)
    * fraction(HLBalance_20D < 0)
)

TopRatio = P / HH_60M
TopProx = clip((TopRatio - 0.95) / 0.05, 0, 1)

Route = 0 unless TopRatio >= 0.95 and HL >= 75
Route = Policy * sqrt(HL/100) * sqrt(TopProx)
Trigger threshold = 55
```

`HLBalance = (NewHighs - NewLows) / (NewHighs + NewLows)`.

Production breadth is reconstructed from the `stock_daily` point-in-time feed using each symbol's **252 prior trading sessions**. A stock contributes to New High / New Low only after 252 prior observations exist.

## Episode evaluation contract

- Daily scores are never deduplicated.
- Statistical episodes use a **126 trading-session lock** after the first `Route >= 55` crossing.
- Re-crossings during the lock belong to the same episode.
- Outcome classes remain: Major Bear (`12M MDD <= -20%`), Severe Near Miss (`-20% < MDD <= -15%`), Correction (`-15% < MDD <= -10%`), False Positive (`MDD > -10%`).

## Frozen audit anchors

- 2006-06-29 control: route ~44.4 (blocked).
- 2018-10-05: route ~66.1, post-top severe-near-miss confirmation.
- 2021-12-15: route ~69.4, ~12 sessions before the 2022-01-03 top.
- 2026-09-10: live route ~60.9; this signal was observed before the final freeze, so only the future path after 2026-10-17 accumulates prospective evidence.

No threshold changes are permitted based on post-freeze outcomes. Any future research variant must use a new version number and keep V2.1.8 unchanged.
