"""Verify WIKI broad-universe 2000–2018 source's exact no-lookahead prices."""
import random
from collections import deque
import pandas as pd
import pytest
from research.v218_wiki_2000_2018_real_price_replay import StockRolling,STATUS,START,END


def naive(values,p):
    if len(values)<252:return False,False,False
    prev=values[-252:]
    return True,p>=max(prev),p<=min(prev)


def test_252_strictly_previous_prices_and_inclusive_equal_extrema():
    st=StockRolling()
    for _ in range(252):
        assert st.update(10.0)==(False,False,False)
    assert st.update(10.0)==(True,True,True)
    assert st.update(9.0)==(True,False,True)
    assert st.update(11.0)==(True,True,False)


def test_random_reference_252_deque_matches_naive_range():
    rng=random.Random(48)
    s=StockRolling()
    prior=[]
    for _ in range(1400):
        price=round(rng.uniform(8,92),3)
        observed=s.update(price)
        assert observed==naive(prior,price)
        prior.append(price)


def test_invalid_price_refuses_to_create_false_signal():
    for p in (0,-1,float('nan')):
        with pytest.raises(ValueError):
            StockRolling().update(p)


def test_real_source_scope_must_not_cross_boundary_2018():
    assert END=='2018-03-27'
    assert START=='2000-01-03'
    assert "NOT_ALL_US_PIT" in STATUS
