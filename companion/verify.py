"""Independent check of a finished run. It shares no code with utr_baselines.py.

It re-reads the pinned source parquet, rebuilds the historical split, checks the
grouped split with a separate breadth-first grouping, recomputes the main test
metrics from saved predictions and source labels, and refits one ridge baseline
with scikit-learn.

    python verify.py --inputs runs/inputs --work runs/full
"""

import argparse
import hashlib
import json
from collections import defaultdict, deque
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from scipy.stats import spearmanr
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PUBLISHED_REPLAY_MSE = 1.914439715839851  # rewire-benchmarks ca73fa4, mrnabench-composition/report.json
TOL = 1e-9


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inputs", type=Path, required=True)
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args()
    out = {"checks": []}

    def check(name, ok, detail):
        out["checks"].append({"check": name, "passed": bool(ok), "detail": detail})
        print(("PASS " if ok else "FAIL ") + name + ": " + str(detail))

    table = pq.read_table(args.inputs / "mrl-sample-designed.parquet", columns=["sequence", "target_mrl_designed"])
    seq = table.column("sequence").to_pylist()
    y_all = np.asarray(table.column("target_mrl_designed").to_pylist(), dtype=float)
    n = len(seq)
    records = pd.read_parquet(args.work / "records.parquet")
    smoke = len(records) != n

    # historical split
    tr, held = train_test_split(np.arange(n), test_size=0.3, random_state=2541)
    va, te = train_test_split(held, test_size=0.5, random_state=2541)
    member = {"train": tr.tolist(), "validation": va.tolist(), "test": te.tolist()}
    digest = hashlib.sha256(json.dumps(member, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    check("historical split hash", digest == "00e287b18ba4e90cb682af6e3fcdfc97e07f2b4b25d13265cd0eca37996536a2", digest)
    hist = np.empty(n, dtype=object)
    for k, v in member.items():
        hist[v] = k
    check("historical labels match records", (records.split_historical.to_numpy() == hist[records.source_index]).all(), "")

    # grouped split: BFS over shared mother or shared 20-mer
    if not smoke:
        geo = pd.read_csv(args.inputs / "GSM3130443_designed_library.csv.gz", usecols=["utr", "mother"])
        mother_of = dict(zip(geo.utr.str[:50], geo.mother.str[:50]))
        inserts = [s[25:75] for s in seq]
        buckets = defaultdict(list)
        for i, s in enumerate(inserts):
            buckets["m:" + mother_of[s]].append(i)
            for p in range(31):
                buckets["k:" + s[p:p + 20]].append(i)
        adj = defaultdict(set)
        for members in buckets.values():
            for j in members[1:]:
                adj[members[0]].add(j)
                adj[j].add(members[0])
        comp = np.full(n, -1)
        c = 0
        for start in range(n):
            if comp[start] >= 0:
                continue
            comp[start] = c
            queue = deque([start])
            while queue:
                i = queue.popleft()
                for j in adj[i]:
                    if comp[j] < 0:
                        comp[j] = c
                        queue.append(j)
            c += 1
        # Compare partitions in O(n) storage; a dense 33,575 x 33,575
        # contingency table would require roughly 9 GB before temporaries.
        partitions = pd.DataFrame({"rebuilt": comp, "recorded": records.component.to_numpy()})
        same_partition = (partitions.groupby("rebuilt").recorded.nunique().eq(1).all() and
                          partitions.groupby("recorded").rebuilt.nunique().eq(1).all())
        check("grouped components reproduced by separate BFS", same_partition, f"{c} components")
        spans = records.groupby("component").split_grouped.nunique().max()
        check("no component spans grouped splits", spans == 1, f"max splits per component {spans}")

    # metrics recomputed from predictions and source labels
    metrics = json.loads((args.work / "metrics.json").read_text())
    worst = 0.0
    for split, s in metrics["splits"].items():
        test_idx = records.loc[records[f"split_{split}"] == "test", "source_index"].to_numpy()
        train_idx = records.loc[records[f"split_{split}"] == "train", "source_index"].to_numpy()
        y = y_all[test_idx]
        cut = np.percentile(y_all[train_idx], 90)
        k = max(int(np.floor(0.01 * len(test_idx))), 1)
        for m, reported in s["methods"].items():
            pr = pd.read_parquet(args.work / "runs" / split / m / "predictions.parquet").set_index("source_index")
            p = pr.loc[test_idx, "prediction"].to_numpy()
            mse = float(np.mean((p - y) ** 2))
            r2 = 1 - np.sum((p - y) ** 2) / np.sum((y - y.mean()) ** 2)
            order = sorted(range(len(p)), key=lambda i: (-p[i], test_idx[i]))[:k]
            prec = float(np.mean(y[order] >= cut))
            diffs = [abs(mse - reported["mse"]), abs(r2 - reported["r2"]), abs(prec - reported["precision_at_k"])]
            if reported["spearman"] is None:
                diffs.append(0.0 if np.ptp(p) == 0 else 1.0)
            else:
                diffs.append(abs(spearmanr(y, p)[0] - reported["spearman"]))
            worst = max(worst, max(diffs))
            if split == "historical" and m == "comp_full_replay" and not smoke:
                check("replay reproduces published historical MSE", abs(mse - PUBLISHED_REPLAY_MSE) < TOL,
                      f"{mse!r} vs {PUBLISHED_REPLAY_MSE!r}")
    check("metrics recomputed independently", worst < TOL, f"max abs difference {worst:.3g}")

    # refit comp_utr with scikit-learn at the recorded alpha
    for split in metrics["splits"]:
        fit = json.loads((args.work / "runs" / split / "comp_utr" / "fit.json").read_text())
        sel = records[f"split_{split}"].to_numpy()
        ins = records["insert"].to_numpy()
        x = np.array([[s.count(b) / 50 for b in "ACGT"] + [(s.count("C") + s.count("G")) / 50] for s in ins])
        sc = StandardScaler().fit(x[sel == "train"])
        model = Ridge(alpha=fit["alpha"]).fit(sc.transform(x[sel == "train"]), records.mrl.to_numpy()[sel == "train"])
        pr = pd.read_parquet(args.work / "runs" / split / "comp_utr" / "predictions.parquet").set_index("source_index")
        idx = records.source_index.to_numpy()[sel == "test"]
        diff = np.abs(model.predict(sc.transform(x[sel == "test"])) - pr.loc[idx, "prediction"].to_numpy()).max()
        check(f"{split} comp_utr refit with scikit-learn", diff < 1e-6, f"max abs prediction difference {diff:.3g}")

    out["all_passed"] = all(c["passed"] for c in out["checks"])
    (args.work / "verify.json").write_text(json.dumps(out, indent=2) + "\n")
    print("ALL PASSED" if out["all_passed"] else "SOME CHECKS FAILED")
    raise SystemExit(0 if out["all_passed"] else 1)


if __name__ == "__main__":
    main()
