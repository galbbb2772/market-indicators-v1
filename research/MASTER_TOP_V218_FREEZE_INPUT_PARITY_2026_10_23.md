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

## Archived freeze provenance resolved

The authentic original merged [PR #8, **2026-10-17 07:16:57 UTC**](https://github.com/galbbb2772/market-indicators-v1/pull/8) explicitly **added** the frozen production code with:

- `["date", "symbol", "close"]` as the MarketParquet input fields;
- `prior_hi = rolling_252(max(prev closing prices))`;
- `new_high = close >= prior_hi`;
- `new_low = close <= prior_lo`.

This predates the later `master-top-v218-live-source` branch, which substitutes intraday high/low price observations. **Therefore the original 2026-10-17 frozen implementation used CLOSING-price-based 252-session extremes, with inclusive comparisons on both sides.** Its written specification only states the 252 prior observations and does not explicitly contradict this implementation; the authentic code is the best dated evidence of the freeze-time comparator definition.

**Resolution of version lineage:** `CLOSE_252_INCLUSIVE_FROZEN` is the original V2.1.8 scorer's source-definition contract. `INTRADAY_252_STRICT_POSTFREEZE_EXPERIMENT` is a distinct, later source-method research candidate. Do not merge its high/low definition into V2.1.8 while claiming frozen input invariance.

This **does not resolve** historical symbol-universe or source completeness. A faithful complete retrospective reproduction still needs date-specific per-symbol closing prices including former/delisted stocks, consistent handling of ticker reuse, and a full first-published-data vs retrospective reconstruction distinction.

## Remaining gate before complete historical scoreboard

1. Recover genuine dated, as-of stock daily `close` observations for the required 252 prior sessions, including delisted/superseded tickers where appropriate. Do not substitute a 2026-survivor list for the historical daily universe.
2. Lock `close >= prior_252_max_close` and `close <= prior_252_min_close` as the **original production reproduction**. Report the statistical impact of inclusive ties rather than changing them after looking at results.
3. Any separate intraday high/low research should use a different `source_definition_id` and must **not** be presented as an unchanged original frozen historical signal.
4. Preserve the original threshold 55, policy/top formula, and 126-session event lock. Do not manufacture missing past alarms.

**Status: ORIGINAL_FREEZE_COMPARATOR_RESTORED_FROM_PR8; STOCK_UNIVERSE_PIT_AND_FULL_DATE_BREADTH_DATA_STILL_OPEN.**
