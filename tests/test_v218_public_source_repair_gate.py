import pandas as pd
import pytest
from research.v218_public_source_repair_gate import repair

def source_rows(n=550,cut=320):
    days=pd.bdate_range("2020-01-01",periods=n)
    vals=[14500]*n; vals[cut]=4390
    a=pd.DataFrame({"date":days,"raw_parquet_rows":vals,
       "archived_issues":vals,"difference_raw_minus_archived":0})
    b=pd.DataFrame({"date":days,"issues":vals,"nh":100,"nl":125})
    c=pd.DataFrame({"date":days,"route_archive_breadth_proxy":0.0,"trigger":False})
    c.loc[350,"trigger"]=True;c.loc[350,"route_archive_breadth_proxy"]=67.44
    return a,b,c

def test_2024_like_single_day_truncation_is_quarantined():
    a,b,c=source_rows()
    out,report=repair(a,b,c)
    assert report["partial_historical_dates_quarantined"][0]["raw_rows"]==4390
    assert out.loc[320,"source_status"]=="QUARANTINED_PARTIAL_DAY_NEEDS_ORIGINAL_REDOWNLOAD"
    assert out.loc[320,"historical_score_kind"]=="QUARANTINED_NO_SCORE"
    assert out.canonical_v218_score.isna().all()
    assert report["qualified_original_frozen_trigger_days"]==0
    assert report["former_exploratory_trigger_days"]==1

def test_sustained_change_is_not_falsely_repaired_by_inventing_bars():
    a,b,c=source_rows()
    a.loc[320:,"raw_parquet_rows"]=5000
    a["difference_raw_minus_archived"]=a.raw_parquet_rows-a.archived_issues
    out,report=repair(a,b,c)
    assert len(report["partial_historical_dates_quarantined"])==0
    assert report["new_historical_security_prices_invented"] is False

def test_bad_matched_grains_never_pass():
    a,b,c=source_rows()
    b=b.iloc[:-1]
    with pytest.raises(ValueError,match="Calendar is not complete"):
        repair(a,b,c)

def test_data_count_arithmetic_must_reconcile():
    a,b,c=source_rows()
    a.loc[20,"difference_raw_minus_archived"]=99
    with pytest.raises(ValueError,match="reconciliation invalid"):
        repair(a,b,c)

def test_frozen_model_and_PIT_are_never_falsely_claimed():
    a,b,c=source_rows()
    _,r=repair(a,b,c)
    assert r["frozen_model_math_threshold_episode_lock_unchanged"]
    assert not r["historic_security_type_normalization_complete"]
    assert not r["PIT_full_US_stock_universe_available"]
    assert r["underlying_2021_signal_correctness"]=="UNDETERMINED"
