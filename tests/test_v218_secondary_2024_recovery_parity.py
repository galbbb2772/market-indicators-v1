import pandas as pd
import pytest
from research.v218_secondary_2024_recovery_parity import secondary_audit,STATUS

def fixture():
    day="2024-11-13"
    tickers=["AAPL","AMZN","MSFT","SPY"]
    sec=pd.DataFrame({"date":[day]*4,"ticker":tickers,
       "close":[225.12,214.10,425.20,590.0],"open":[224.01,209.4,421.64,591.0],
       "high":[226.65,215.09,429.325,595.0],"low":[222.76,209.14,418.21,588.0],
       "volume":[1000]*4,"otc":[False]*4,"utc_timestamp_ms":[1731531600000]*4})
    orig=pd.DataFrame({"date":[day]*2,"ticker":["AAPL","MSFT"],"close":[225.12,425.20]})
    return sec,orig

def test_real_provider_candidate_never_autopromotes_as_original():
    s,a=fixture()
    r=secondary_audit(s,a,min_secondary_rows=3)
    assert r["status"]==STATUS
    assert r["actual_private_recovery_rows"]==4
    assert r["comparison_overlap"]==2
    assert r["secondary_symbols_not_in_corrupt_archive"]==2
    assert r["split_adjusted_price_parity_verified"] is True
    assert r["automatically_replace_canonical_archive"] is False
    assert r["pit_common_stock_universe_verified"] is False

def test_wrong_day_cannot_enter_original_historical_file():
    s,a=fixture()
    s.loc[1,"date"]="2024-11-14"
    with pytest.raises(ValueError,match="exact supported date"):
        secondary_audit(s,a,min_secondary_rows=3)

def test_duplicate_security_identifier_requires_manual_resolution():
    s,a=fixture()
    s.loc[0,"ticker"]="MSFT"
    with pytest.raises(ValueError,match="duplicate ticker"):
        secondary_audit(s,a,min_secondary_rows=3)

def test_mismatched_source_prices_do_not_count_as_parity():
    s,a=fixture()
    s.loc[0,"close"]*=1.12
    r=secondary_audit(s,a,min_secondary_rows=3)
    assert r["split_adjusted_price_parity_verified"] is False
    assert r["automatically_replace_canonical_archive"] is False

def test_zero_open_with_positive_close_is_flagged_not_silently_dropped():
    s,a=fixture()
    s.loc[0,"open"]=0
    r=secondary_audit(s,a,min_secondary_rows=3)
    assert r["unusual_open_price_symbols"]==["AAPL"]
