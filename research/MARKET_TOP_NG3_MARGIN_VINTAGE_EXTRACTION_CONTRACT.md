# NG3: historical margin-vintage extraction contract (2026-10-19)

**Research only. No production or scoring change.**

## Primary sources to transcribe

- [April 1976 Survey of Current Business](https://fraser.stlouisfed.org/title/survey-current-business-46/april-1976-9659): contents list *Current-Dollar Cost and Profit per Unit of Constant Dollar Gross Domestic Product of Nonfinancial Corporate Business* on page 20. The original table, not OCR stream order, is the extraction authority.
- [June 1988 Survey of Current Business](https://fraser.stlouisfed.org/title/survey-current-business-46/june-1988-10086/fulltext): *Table 7.18 — Current-Dollar Cost and Profit Per Unit of Constant-Dollar Gross Domestic Product of Nonfinancial Corporate Business*.
- [August 1996 Survey of Current Business, page 69](https://apps-fd.bea.gov/scb/issues/1996/scb-1996-august.pdf): *Table 7.15* (later table numbering), explicit line 1 total cost-and-profit per unit, line 7 profits with IVA and CCAdj, line 9 after-tax profits.
- Current revised FRED/BEA annual series [A463RD3A052NBEA](https://fred.stlouisfed.org/data/A463RD3A052NBEA) is **revision diagnostic only**, never a historical release-vintage substitute.

## Required extraction record

For each observation, retain:

```
publication_year_month
publication_url
publication_page
table_number_as_printed
table_title_as_printed
row_label_as_printed
column_year
column_quarter
seasonal_adjustment_status
profit_concept  # IVA_ONLY / IVA_CCADJ / UNKNOWN
denominator_concept
unit_profit_printed
total_cost_and_profit_per_unit_printed
profit_share_computed
transcription_status # VERIFIED / AMBIGUOUS / MISSING
independent_crosscheck
```

Calculate profit_share only if numerator and denominator come from the **same printed column and vintage**. Mark ambiguous OCR columns as AMBIGUOUS; never guess or forward-fill. Do not treat publication month as the observation quarter. A value cannot enter a PIT feature until the actual publication date is established; use a conservative later availability date when day is unknown.

## Acceptance criteria

1. Original page image confirms the 1976 and 1988 quarter-to-column mapping.
2. Row/column intersection independently cross-checked for at least two quarters per vintage.
3. Same-vintage profit-share calculations recompute to machine precision.
4. Any modern-series comparison is explicitly marked *revision/concept diagnostic* and restricted to compatible definitions.
5. Report earliest comparable MarginConfirm observation; keep older periods MARGIN_NOT_COMPARABLE.

**Status:** SOURCE_DISCOVERED; NUMERIC_TRANSCRIPTION_PENDING; PIT_VALIDATION_PENDING; FORMULA_NOT_FROZEN; HISTORICAL_HIT_RATE_NOT_TESTED.

Do not merge this research branch into production on the strength of the source discovery alone.
