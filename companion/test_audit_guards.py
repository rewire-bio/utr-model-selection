"""Synthetic regression checks for complete, finite, provenance-bound analysis."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import utr_baselines as ub
import verify


def records():
    return pd.DataFrame({"source_index": [0, 1, 2], "split_historical": ["train", "validation", "test"]})


def predictions():
    return pd.DataFrame({"source_index": [1, 2], "split": ["validation", "test"], "prediction": [2., 3.]})


@pytest.mark.parametrize("kind", ["missing", "extra", "duplicate", "wrong_split", "nan", "inf", "seed_nan"])
def test_reject_invalid_predictions(kind):
    pr = predictions()
    if kind == "missing": pr = pr.iloc[:1]
    elif kind == "extra": pr.loc[2] = [3, "test", 1.]
    elif kind == "duplicate": pr.loc[1, "source_index"] = 1
    elif kind == "wrong_split": pr.loc[1, "split"] = "validation"
    elif kind in ("nan", "inf"): pr.loc[1, "prediction"] = float(kind)
    else: pr["prediction_seed1"] = [1., np.nan]
    with pytest.raises(ValueError): ub.validate_predictions(records(), pr, "historical")


def test_prediction_alignment_accepts_arbitrary_file_order():
    ub.validate_predictions(records(), predictions().iloc[::-1], "historical")


def test_verifier_nonfinite_discrepancies_fail():
    for value in (np.nan, np.inf, -np.inf):
        assert verify.finite_max_difference([0., value]) == np.inf
    assert verify.finite_max_difference([0., 0.1]) == 0.1


def test_verifier_requires_declared_population_and_exact_labels():
    seq = ["A" * 855, "C" * 855]
    labels = np.array([2., 3.])
    rec = pd.DataFrame({"source_index": [0, 1], "mrl": labels, "insert": ["A"*50, "C"*50]})
    assert verify.validate_population(rec, seq, labels, {"smoke": False}) is False
    with pytest.raises(ValueError): verify.validate_population(rec.iloc[:1], seq, labels, {"smoke": False})
    with pytest.raises(ValueError): verify.validate_population(rec, seq, labels, {})
    rec.loc[0, "mrl"] = 9.
    with pytest.raises(ValueError): verify.validate_population(rec, seq, labels, {"smoke": False})


def test_fresh_artifact_guard_does_not_overwrite(tmp_path):
    ub.require_fresh(tmp_path)
    p = tmp_path / "evidence.txt"
    p.write_text("keep")
    with pytest.raises(ValueError): ub.require_fresh(tmp_path)
    assert p.read_text() == "keep"


def test_cache_rejects_record_reorder_and_changed_bytes(tmp_path):
    records().to_parquet(tmp_path / "records.parquet")
    cache = tmp_path / "cache"
    cache.mkdir()
    for name in ("utrlm_mean.npy", "utrlm_pos.f16.npy"):
        np.save(cache / name, np.zeros((3, 2)))
    receipt = {"records_sha256": ub.sha256_file(tmp_path / "records.parquet"),
               "cache_sha256": {p.name: ub.sha256_file(p) for p in cache.iterdir()}}
    (tmp_path / "embed.json").write_text(json.dumps(receipt))
    ub.validate_cache(tmp_path)
    records().iloc[::-1].to_parquet(tmp_path / "records.parquet")
    with pytest.raises(ValueError, match="records"): ub.validate_cache(tmp_path)
    records().to_parquet(tmp_path / "records.parquet")
    (cache / "utrlm_mean.npy").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="checksum"): ub.validate_cache(tmp_path)


def test_evaluate_rejects_missing_split(tmp_path):
    records().to_parquet(tmp_path / "records.parquet")
    with pytest.raises(ValueError, match="Missing registered split"): ub.evaluate(tmp_path)


def test_evaluate_rejects_missing_method(tmp_path, monkeypatch):
    r = records().assign(mrl=[2., 3., 4.], component=[0, 1, 2])
    r.to_parquet(tmp_path / "records.parquet")
    (tmp_path / "runs/historical").mkdir(parents=True)
    monkeypatch.setattr(ub, "cluster_bootstrap", lambda *a: np.ones((2, 1)))
    with pytest.raises(ValueError, match="Missing registered fit"): ub.evaluate(tmp_path)


def test_bootstrap_precision_matches_explicit_cluster_replication():
    p = np.array([4., 4., 2., 1.])
    high = np.array([0., 1., 1., 0.])
    indices = np.array([8, 2, 4, 1])
    codes = np.array([0, 1, 1, 2])
    weights = np.array([[2, 1, 0], [0, 2, 3]], dtype=float)
    actual = ub.boot_precision(p, high, indices, codes, weights, frac=.5)
    expected = []
    for row in weights:
        repeated = np.repeat(np.arange(4), row[codes].astype(int))
        k = max(int(.5 * len(repeated)), 1)
        expected.append(ub.precision_at_k(p[repeated], high[repeated], indices[repeated], k))
    np.testing.assert_array_equal(actual, expected)


def test_legacy_evaluation_never_bypasses_recorded_hash_mismatch(tmp_path, monkeypatch):
    r = records().assign(mrl=[2., 3., 4.], component=[0, 1, 2])
    r.to_parquet(tmp_path / "records.parquet")
    method = tmp_path / "runs/historical/train_mean"
    method.mkdir(parents=True)
    (method / "fit.json").write_text(json.dumps({"val_mse": 1., "records_sha256": "wrong"}))
    monkeypatch.setattr(ub, "cluster_bootstrap", lambda *a: np.ones((2, 1)))
    with pytest.raises(ValueError, match="mismatched records_sha256"):
        ub.evaluate(tmp_path, allow_legacy_artifacts=True)


def test_independent_grouping_and_allocation_match_registered_rule():
    rng = np.random.default_rng(11)
    inserts = [''.join(rng.choice(list('ACGT'), 50)) for _ in range(400)]
    inserts[1] = inserts[0][:20] + inserts[1][20:]
    mothers = {s: s for s in inserts}
    mothers[inserts[3]] = inserts[2]
    groups = verify.rebuild_components(inserts, mothers)
    np.testing.assert_array_equal(groups, ub.link_components(np.array(inserts), np.array([mothers[s] for s in inserts])))
    np.testing.assert_array_equal(verify.grouped_allocation(groups), ub.grouped_split(groups))
