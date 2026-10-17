import math
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from master_top_v218 import (
    hl_persistence_score,
    policy_score,
    rate_shock_1m,
    rate_shock_6m,
    route_score,
    top_proximity,
)


def test_rate_components():
    assert math.isclose(rate_shock_6m(54), 73.3333333333, rel_tol=1e-9)
    assert math.isclose(rate_shock_1m(18), 90.0, rel_tol=1e-9)
    assert math.isclose(policy_score(54, 18), math.sqrt(73.3333333333 * 90), rel_tol=1e-8)


def test_top_proximity_continuous():
    assert top_proximity(0.95) == 0
    assert math.isclose(top_proximity(0.975), 0.5, rel_tol=1e-12)
    assert top_proximity(1.0) == 1


def test_control_2006_is_below_trigger():
    s = route_score(policy=100.0, hl_score=97.4679434481, top_ratio=0.9601)
    assert 44.0 < s < 45.0
    assert s < 55.0


def test_2021_12_15_major_bear_warning_survives():
    s = route_score(policy=75.72, hl_score=84.84, top_ratio=0.9995)
    assert 69.0 < s < 70.0
    assert s >= 55.0


def test_2026_09_10_live_signal_survives():
    s = route_score(policy=100.0, hl_score=76.49, top_ratio=0.9742)
    assert 60.0 < s < 62.0
    assert s >= 55.0


def test_hl_persistence_definition():
    vals = [-0.30] * 15 + [0.10] * 5
    score = hl_persistence_score(vals)
    mean = sum(vals) / 20
    neg_frac = 15 / 20
    expected = 100 * math.sqrt(min(1, max(0, -mean / 0.30)) * neg_frac)
    assert math.isclose(score, expected, rel_tol=1e-12)
