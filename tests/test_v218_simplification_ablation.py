import pandas as pd
import numpy as np
from research.v218_simplification_ablation import build_variants,THRESHOLD,LOCK

def fixture():
    dates=pd.bdate_range("2021-01-01",periods=4)
    base=pd.DataFrame({
        "date":dates,"hl":[80.,80.,80.,80.],"policy":[100.,0.,100.,100.],
        "top_ratio":[1.0,1.0,.90,1.0],"gspc_close":[100,99,98,97]})
    gates=pd.DataFrame({"date":dates,"delta_1m_bp":[20,0,20,20],
                        "delta_6m_bp":[70,70,70,70],"gspc_close":[100,99,98,97]})
    return base,gates

def test_original_requires_all_three_factors():
    b,g=fixture();x=build_variants(b.rename(columns={"hl":"hl_score"}),"hl_score",g)
    assert x.original.iloc[0] > THRESHOLD
    assert x.original.iloc[1] == 0    # policy blocks
    assert x.original.iloc[2] == 0    # top proximity blocks

def test_remove_policy_keeps_top_and_hl_gates():
    b,g=fixture();x=build_variants(b.rename(columns={"hl":"hl_score"}),"hl_score",g)
    assert x.no_policy_factor.iloc[1] > THRESHOLD
    assert x.no_policy_factor.iloc[2] == 0

def test_remove_top_keeps_policy_and_hl():
    b,g=fixture();x=build_variants(b.rename(columns={"hl":"hl_score"}),"hl_score",g)
    assert x.no_top_factor.iloc[2] > THRESHOLD
    assert x.no_top_factor.iloc[1] == 0

def test_breadth_only_is_exact_hl_score():
    b,g=fixture();x=build_variants(b.rename(columns={"hl":"hl_score"}),"hl_score",g)
    assert np.allclose(x.breadth_only.to_numpy(),80.0)

def test_research_constants_do_not_mutate_frozen_model():
    assert THRESHOLD==55.0
    assert LOCK==126
