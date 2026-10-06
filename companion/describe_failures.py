"""Descriptive follow-up on a finished run (reads saved outputs only; fits nothing).

    python describe_failures.py --work runs/full
"""

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

ATG = "ATG"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args()
    rec = pd.read_parquet(args.work / "records.parquet")
    out = {}
    for split in ("historical", "grouped"):
        test = rec[rec[f"split_{split}"] == "test"].copy()
        for m in ("cheap_combined", "cnn", "utrlm_cnn"):
            pr = pd.read_parquet(args.work / "runs" / split / m / "predictions.parquet")
            test = test.merge(pr[["source_index", "prediction"]].rename(columns={"prediction": m}), on="source_index")
        col = rec[f"split_{split}"]
        comp = pd.crosstab(rec.library, col)
        train_y = rec.loc[col == "train", "mrl"]
        cut = float(np.percentile(train_y, 90))
        s = {"records_by_library_and_split": {lib: {k: int(v) for k, v in row.items()} for lib, row in comp.iterrows()},
             "test_mrl_mean_sd": [float(test.mrl.mean()), float(test.mrl.std())],
             "chance_precision_equals_test_high_mrl_share": float((test.mrl >= cut).mean()),
             "cnn_device_parity": {m: {seed: {"val_mse_training_device": v["val_mse_training_device"], "val_mse_cpu": v["val_mse"],
                                             "abs_diff": abs(v["val_mse_training_device"] - v["val_mse"]), "device": v["device"],
                                             "seconds_this_seed": v["seconds"]}
                                       for seed, v in json.loads((args.work / "runs" / split / m / "fit.json").read_text())["seeds"].items()}
                                   for m in ("cnn", "utrlm_cnn")},
             "components_per_library": test.groupby("library").component.nunique().to_dict(),
             "read_depth_quartile_edges": [float(x) for x in np.quantile(test.total_reads, [0, .25, .5, .75, 1])]}
        lib = test[test.library == "step_worst_to_best_allow_uatg"]
        if len(lib):
            err = lib.assign(e=(lib.cnn - lib.mrl) ** 2, e_ref=(lib.cheap_combined - lib.mrl) ** 2)
            by = err.groupby("component").agg(n=("e", "size"), cnn_sse=("e", "sum"), ref_sse=("e_ref", "sum"))
            by = by.sort_values("cnn_sse", ascending=False)
            s["step_worst_allow_uatg"] = {
                "records": int(len(lib)), "components": int(by.shape[0]),
                "largest_component_records": int(by.n.max()),
                "top_component_records": int(by.n.iloc[0]),
                "share_of_cnn_sse_in_top_component": float(by.cnn_sse.iloc[0] / by.cnn_sse.sum()),
                "top_component_cnn_mse": float(by.cnn_sse.iloc[0] / by.n.iloc[0]),
                "top_component_ref_mse": float(by.ref_sse.iloc[0] / by.n.iloc[0]),
                "measured_mrl_mean": float(lib.mrl.mean()), "cnn_pred_mean": float(lib.cnn.mean()),
                "ref_pred_mean": float(lib.cheap_combined.mean()),
                "share_with_uatg": float(lib["insert"].str.contains(ATG).mean()),
            }
        test["abs_cnn_err"] = (test.cnn - test.mrl).abs()
        s["cnn_abs_error_over_2_mrl"] = int((test.abs_cnn_err > 2).sum())
        s["cnn_abs_error_over_2_median_reads"] = float(test.loc[test.abs_cnn_err > 2, "total_reads"].median())
        s["median_reads_all_test"] = float(test.total_reads.median())
        out[split] = s
    sizes = rec.component.value_counts()
    giant = int(sizes.index[0])
    g = rec[rec.component == giant]
    out["largest_component"] = {"records": int(len(g)), "share_of_all_records": float(len(g) / len(rec)),
                                "records_by_library": {k: int(v) for k, v in g.library.value_counts().items()},
                                "mrl_mean_sd": [float(g.mrl.mean()), float(g.mrl.std())],
                                "all_records_mrl_mean_sd": [float(rec.mrl.mean()), float(rec.mrl.std())]}
    out["train_mean_tie_note"] = ("train_mean predicts one constant, so every test record ties; precision_at_k uses the "
                                  "registered source-index tie rule. Its chance expectation is the test high-MRL share.")
    (args.work / "failures.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
