import pandas as pd
import numpy as np
import pytest
from research.v218_weighted_sum_grid import weighted_score,top_score,grid,THRESHOLD

def test_weights_sum_to_one():
    s=weighted_score(pd.Series([100]),pd.Series([100]),pd.Series([1.0]),.3,.5,.2)
    assert float(s.iloc[0])==100
    with pytest.raises(ValueError):weighted_score(pd.Series([1]),pd.Series([1]),pd.Series([1]),.3,.5,.3)

def test_top_is_0_to_100():
    x=top_score(pd.Series([.90,.95,.975,1.0,1.02]))
    assert np.allclose(x,[0,0,50,100,100])

def test_user_initial_example():
    # HL=90, Policy=20, Top=80 -> 67 with 50/30/20 (HL/Policy/Top)
    ratio=.95+.05*.80
    s=weighted_score(pd.Series([20]),pd.Series([90]),pd.Series([ratio]),.30,.50,.20)
    assert abs(float(s.iloc[0])-67)<1e-9

def test_grid_keeps_all_three_factors_nonzero():
    vals=list(grid(.05,.10))
    assert vals and all(min(v)>=.10-1e-9 for v in vals)
    assert all(abs(sum(v)-1)<1e-9 for v in vals)

def test_light_hl_floor_is_optional_not_hidden():
    s1=weighted_score(pd.Series([100]),pd.Series([30]),pd.Series([1.0]),.3,.4,.3,None)
    s2=weighted_score(pd.Series([100]),pd.Series([30]),pd.Series([1.0]),.3,.4,.3,40)
    assert s1.iloc[0]>0 and s2.iloc[0]==0
    assert THRESHOLD==55.0
