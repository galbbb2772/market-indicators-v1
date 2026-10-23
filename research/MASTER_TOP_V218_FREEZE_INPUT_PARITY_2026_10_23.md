# Frozen V2.1.8 source-definition discrepancy — audit 2026-10-23

**OPEN; data-input definition is not yet internally consistent. Do NOT silently mix close-only and intraday 52-week high/low breadth histories.**

## Exact discrepancy in existing canonical files

1. `MASTER_TOP_V2_1_8_SPEC.md` says: production breadth reconstructed from each stock's **252 prior trading sessions**, with NewHigh/NewLow. Its wording does not itself explicitly give the high/low-vs-close comparator, but the term "52-week highs/lows" and later high/low-specific implementation create ambiguity.
2. Production `main:master_top_v218.py`, as inspected 2026-10-23, downloads columns `date,symbol,close` and marks `new_high` on `close >= prior max(close)` and `new_low` on `close <= prior min(close)`. This is **252-prior-session closing-high/closing-low**, including equal prices.
3. Separate `master-top-v218-live-source` research branch downloads `date,symbol,high,low` and marks new high when `high > prior max(high)`; new low when `low < prior min(low)` (strict inequality). This is **intraday high/low methodology**, not the same feed calculation.
4. The current PR #18 (operations-only fail-closed refresh patch) does **not** fix or reconcile the above; it changes input-date gates, not how stock highs/lows are counted.

## Why this matters

Replacing a closing-high/low cohort with intraday-high/low counts silently changes the `HLBalance` and the 20-session `HL` persistence, which can change whether the frozen threshold 55 is reached. No "same frozen signal backtest" can be claimed without first selecting and documenting a canonical input definition and point-in-time symbol universe. A history reconstructed from surviving 2026 tickers also leaks delisting/survivorship bias.

The current all-history partial gate audit (this PR) uses **only ^GSPC and DGS2**, which are invariant to the disputed stock H/L implementation. It explicitly labels actual H/L as unavailable. It therefore does not hide or rewrite this discrepancy.

## Resolution gate before complete historical scoreboard

- Produce controlled, *same-symbol/date* comparisons of `close >= previous 252 closing highs` vs `intraday high > previous 252 highs` and corresponding lows, for 2018 and 2021–22.
- Recover the authentic source-definition freeze decision from source history/commits if possible; if the original definition is irreducibly ambiguous, preserve `CLOSE_252` historical source as one labeled research reconstruction and test `INTRADAY_252` as **different source family**, not falsely identical retrospective scores.
- Keep the threshold, policy/top gate, episode lock and prior score anchors untouched; disclose any difference in scores rather than selecting a better-looking variant after observing outcomes.

**Status: SOURCE_DEFINITION_CONFLICT; no official complete historical V2.1.8 effectiveness estimates yet.**
