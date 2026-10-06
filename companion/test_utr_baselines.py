"""Unit tests for utr_baselines.py. Data-dependent tests skip unless UTR_WORK points at a finished run."""

import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import utr_baselines as ub

RNG = np.random.default_rng(0)


def random_insert(rng=RNG):
    return "".join(rng.choice(list("ACGT"), 50))


def test_historical_split_matches_published_hash():
    membership, digest = ub.historical_split(100017)
    assert digest == ub.HISTORICAL_SPLIT_SHA256
    assert [len(membership[k]) for k in ("train", "validation", "test")] == [70011, 15003, 15003]


def test_components_link_shared_20mer_and_mother():
    a = random_insert()
    b = a[:20] + random_insert()[20:]  # shares the first 20 nt with a
    c = random_insert()
    d = random_insert()
    comp = ub.link_components(np.array([a, b, c, d]), np.array(["m1", "m2", "m3", "m3"]))
    assert comp[0] == comp[1]
    assert comp[2] == comp[3]  # same mother
    assert comp[0] != comp[2]


def test_grouped_split_keeps_components_whole_and_sends_giant_to_train():
    comp = np.concatenate([np.zeros(50, int), np.repeat(np.arange(1, 951), 1)])
    split = ub.grouped_split(comp)
    assert set(split[:50]) == {"train"}  # 50/1000 records > 1%
    frame = pd.DataFrame({"c": comp, "s": split})
    assert frame.groupby("c").s.nunique().max() == 1
    assert 140 <= (split == "test").sum() <= 160


def test_annotation_features_frame_and_kozak():
    # ATG at position 45 is 5 nt before the main AUG: out of frame. ATG at 41 is 9 nt: in frame.
    base = "C" * 50
    oof = base[:45] + "ATG" + base[48:]
    inframe = base[:41] + "ATG" + base[44:47] + "ACC"
    f_oof, f_in, f_none = ub.annot_features([oof, inframe, base])
    assert f_oof[0] == 1 and f_oof[1] == 1 and f_oof[2] == 0
    assert f_in[0] == 1 and f_in[1] == 0 and f_in[2] == 1
    assert f_none[0] == 0
    assert f_in[5] == 1  # -3 position is A (purine)
    assert f_none[5] == 0  # -3 position is C


def test_kmer_counts_sum():
    x = ub.kmer_features([random_insert(), random_insert()])
    assert x.shape == (2, 84)
    assert np.allclose(x.sum(1), 50 + 49 + 48)


def test_ridge_select_matches_sklearn():
    from sklearn.linear_model import Ridge
    from sklearn.preprocessing import StandardScaler
    x = RNG.normal(size=(300, 6))
    y = x @ RNG.normal(size=6) + RNG.normal(size=300)
    tr, va = np.arange(200), np.arange(200, 300)
    alpha, _, predict = ub.ridge_select(lambda i: x[i], tr, va, y[tr], y[va], chunk=64)
    sc = StandardScaler().fit(x[tr])
    ref = Ridge(alpha=alpha).fit(sc.transform(x[tr]), y[tr]).predict(sc.transform(x[va]))
    assert np.allclose(predict(va), ref, atol=1e-8)


def test_constant_predictions_have_undefined_correlation():
    m = ub.regression_metrics(np.array([1.0, 2.0, 3.0]), np.array([2.0, 2.0, 2.0]))
    assert m["pearson"] is None and m["spearman"] is None
    assert m["mse"] == pytest.approx(2 / 3)


def test_precision_ties_break_to_lower_index():
    p = np.array([1.0, 1.0, 0.5, 0.2])
    high = np.array([0.0, 1.0, 1.0, 0.0])
    assert ub.precision_at_k(p, high, np.array([10, 3, 5, 7]), 1) == 1.0
    assert ub.precision_at_k(p, high, np.array([3, 10, 5, 7]), 1) == 0.0


def test_bootstrap_precision_with_unit_weights_equals_point_estimate():
    n = 400
    p = RNG.normal(size=n)
    high = (RNG.random(n) < 0.1).astype(float)
    codes = np.arange(n)
    w = np.ones((3, n))
    got = ub.boot_precision(p, high, np.arange(n), codes, w)
    assert np.allclose(got, ub.precision_at_k(p, high, np.arange(n), 4))


def test_verdicts():
    assert ub._verdict(0.2, 0.05, 0.3, 0.1) == "adds practical value"
    assert ub._verdict(0.05, 0.01, 0.1, 0.1) == "difference below practical threshold"
    assert ub._verdict(0.05, -0.01, 0.1, 0.1) == "no supported difference"
    assert ub._verdict(-0.2, -0.3, -0.1, 0.1) == "worse than reference"


WORK = os.environ.get("UTR_WORK")


@pytest.mark.skipif(not WORK, reason="set UTR_WORK to a finished full run")
def test_full_run_outputs():
    work = Path(WORK)
    prep = json.loads((work / "prepare.json").read_text())
    assert prep["checks"]["geo_rl_max_abs_diff"] == 0.0
    metrics = json.loads((work / "metrics.json").read_text())
    replay = metrics["splits"]["historical"]["methods"]["comp_full_replay"]
    assert abs(replay["mse"] - 1.914439715839851) < 1e-9
    assert metrics["splits"]["historical"]["methods"]["train_mean"]["pearson"] is None
    for split in ("historical", "grouped"):
        for m in metrics["splits"][split]["methods"].values():
            assert m["coverage"].split("/")[0] == m["coverage"].split("/")[1]
