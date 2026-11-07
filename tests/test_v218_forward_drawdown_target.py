import numpy as np
from research.v218_forward_drawdown_target import first_passage_days,summarize

def test_first_passage_is_from_signal_close_and_uses_future_sessions_only():
    close=np.array([100,99,96,94,93,90],dtype=float)
    d5=first_passage_days(close,.05,5)
    d10=first_passage_days(close,.10,5)
    assert d5[0]==3   # 94 is first <=95
    assert d10[0]==5  # 90 is first <=90
    assert d5[3]!=0   # current day never counts as future hit

def test_no_hit_is_nan():
    close=np.array([100,101,102,103],dtype=float)
    x=first_passage_days(close,.05,3)
    assert np.isnan(x[0])

def test_probability_denominator_requires_full_forward_horizon():
    close=np.array([100,94,93,92,91],dtype=float)
    f={.05:first_passage_days(close,.05,4),.10:first_passage_days(close,.10,4),.15:first_passage_days(close,.15,4)}
    r=summarize([0,3],f,len(close),3)
    assert r["fully_observable"]==1
    assert r["hit_5_pct"]==100.0

def test_market_session_wait_is_integer_first_hit():
    close=np.array([100,99,98,97,96,95],dtype=float)
    x=first_passage_days(close,.05,5)
    assert x[0]==5
