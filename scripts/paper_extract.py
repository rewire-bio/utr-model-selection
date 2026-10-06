#!/usr/bin/env python3
"""Format archived historical results into LaTeX tables for the imported-evidence paper.

Formatting and extraction only; nothing is recomputed. Values are read from members of the
archived `downloads/utr-baselines-results.zip` (read in memory, never extracted). The archive
digest is checked against `evidence/import-manifest.json` and every member used against the
member digests recorded in `evidence/migration-audit.json`. Generated strings are cross-checked
against the values printed in the original article (transcribed below as ARTICLE_*); any
disagreement stops the build. Standard library only; no network, no environment creation.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIPPATH = "downloads/utr-baselines-results.zip"
PREFIX = "utr-baselines-results/"
GEN = ROOT / "paper/generated"
SPLITS = ("historical", "grouped")
ORDER = ["train_mean", "comp_utr", "kmer_utr", "onehot_pos", "annot", "cheap_combined", "cnn",
         "utrlm_mean_ridge", "utrlm_pos_ridge", "utrlm_cnn"]
NAMES = {"train_mean": "Training mean", "comp_full_replay": "Composition, full sequence (replay)",
         "comp_utr": "Composition", "kmer_utr": "1--3-mer counts", "onehot_pos": "Positional one-hot",
         "annot": "uAUG/Kozak features", "cheap_combined": "Cheap combined (reference)",
         "cnn": "CNN, one-hot (seed 0)", "utrlm_mean_ridge": "UTR-LM mean + ridge",
         "utrlm_pos_ridge": "UTR-LM per-position + ridge", "utrlm_cnn": "UTR-LM + CNN head (seed 0)"}
SHORT = {"cheap_combined": "cheap combined", "cnn": "CNN", "utrlm_cnn": "UTR-LM + CNN",
         "utrlm_pos_ridge": "UTR-LM per-position + ridge", "utrlm_mean_ridge": "UTR-LM mean + ridge",
         "comp_utr": "Composition", "kmer_utr": "1--3-mer counts", "onehot_pos": "Positional one-hot",
         "annot": "uAUG/Kozak features"}

# Values as printed in the original article's Table 2 (random | grouped): MSE [CI], R2, P@150 [CI].
ARTICLE_T2 = {
    "train_mean": ("2.366 [2.234, 2.481]", "0.000", "0.053 [0.008, 0.094]", "2.224 [2.096, 2.384]", "-0.022", "0.040 [0.013, 0.077]", "0.0 / 0.0", "0.22 / 0.22"),
    "comp_utr": ("1.914 [1.834, 2.004]", "0.190", "0.327 [0.172, 0.401]", "1.888 [1.807, 1.975]", "0.132", "0.233 [0.143, 0.327]", "0.2 / 0.1", "0.36 / 0.35"),
    "kmer_utr": ("1.225 [1.177, 1.267]", "0.482", "0.533 [0.427, 0.600]", "1.162 [1.111, 1.210]", "0.466", "0.540 [0.444, 0.636]", "13.2 / 13.0", "0.27 / 0.28"),
    "onehot_pos": ("1.769 [1.709, 1.839]", "0.252", "0.360 [0.154, 0.532]", "1.767 [1.702, 1.836]", "0.188", "0.360 [0.234, 0.452]", "1.1 / 0.4", "0.37 / 0.37"),
    "annot": ("1.280 [1.228, 1.326]", "0.459", "0.340 [0.258, 0.417]", "1.193 [1.138, 1.248]", "0.452", "0.307 [0.220, 0.380]", "1.4 / 0.7", "0.30 / 0.30"),
    "cheap_combined": ("0.849 [0.808, 0.888]", "0.641", "0.580 [0.386, 0.689]", "0.776 [0.739, 0.814]", "0.643", "0.553 [0.456, 0.651]", "14.6 / 20.7", "0.55 / 0.45"),
    "cnn": ("0.427 [0.389, 0.465]", "0.819", "0.787 [0.617, 0.866]", "0.560 [0.529, 0.595]", "0.743", "0.573 [0.470, 0.669]", "205 / 250", "1.32 / 1.18"),
    "utrlm_mean_ridge": ("1.184 [1.143, 1.222]", "0.499", "0.460 [0.312, 0.547]", "1.139 [1.093, 1.183]", "0.477", "0.347 [0.242, 0.466]", "0.6 / 0.2", "0.30 / 0.29"),
    "utrlm_pos_ridge": ("0.939 [0.904, 0.981]", "0.603", "0.513 [0.367, 0.614]", "1.020 [0.981, 1.061]", "0.531", "0.380 [0.307, 0.480]", "106.1 / 89.5", "3.22 / 2.75"),
    "utrlm_cnn": ("0.407 [0.376, 0.440]", "0.828", "0.660 [0.512, 0.771]", "0.570 [0.539, 0.602]", "0.738", "0.567 [0.487, 0.680]", "269 / 263", "2.18 / 2.19"),
}
# Article Table 3: (method, reference, split) -> (MSE reduction [CI], verdict, P@150 gain [CI], verdict)
ARTICLE_T3 = [
    ("cnn", "cheap_combined", "historical", "+0.422 [+0.363, +0.488]", "adds practical value", "+0.207 [+0.124, +0.292]", "adds practical value"),
    ("cnn", "cheap_combined", "grouped", "+0.216 [+0.176, +0.252]", "adds practical value", "+0.020 [-0.088, +0.132]", "no supported difference"),
    ("utrlm_cnn", "cheap_combined", "historical", "+0.443 [+0.388, +0.502]", "adds practical value", "+0.080 [+0.000, +0.208]", "no supported difference"),
    ("utrlm_cnn", "cheap_combined", "grouped", "+0.206 [+0.173, +0.237]", "adds practical value", "+0.013 [-0.087, +0.149]", "no supported difference"),
    ("utrlm_pos_ridge", "cheap_combined", "historical", "-0.090 [-0.144, -0.033]", "worse", "-0.067 [-0.141, +0.056]", "no supported difference"),
    ("utrlm_pos_ridge", "cheap_combined", "grouped", "-0.244 [-0.272, -0.216]", "worse", "-0.173 [-0.278, -0.047]", "worse"),
    ("utrlm_mean_ridge", "cheap_combined", "historical", "-0.335 [-0.371, -0.305]", "worse", "-0.120 [-0.203, -0.015]", "worse"),
    ("utrlm_mean_ridge", "cheap_combined", "grouped", "-0.363 [-0.400, -0.327]", "worse", "-0.207 [-0.335, -0.073]", "worse"),
    ("utrlm_cnn", "cnn", "historical", "+0.021 [+0.009, +0.034]", "below practical threshold", "-0.127 [-0.179, -0.023]", "worse"),
    ("utrlm_cnn", "cnn", "grouped", "-0.010 [-0.034, +0.016]", "no supported difference", "-0.007 [-0.103, +0.122]", "no supported difference"),
]
VERDICT = {"adds practical value": "adds practical value", "worse than reference": "worse",
           "no supported difference": "no supported difference",
           "difference below practical threshold": "below practical threshold"}


def sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def num(x: float, nd: int = 3) -> str:
    s = f"{x:.{nd}f}"
    return "0." + "0" * nd if s == "-0." + "0" * nd else s


def signed(x: float, nd: int = 3) -> str:
    s = f"{x:+.{nd}f}"
    return "+0." + "0" * nd if s == "-0." + "0" * nd else s


def tex(s: str) -> str:
    """Typeset numbers with a true minus sign."""
    out = []
    for tok in s.split(" "):
        core = tok.strip("[],")
        if core[:1] in "+-" and core[1:2].isdigit():
            tok = tok.replace(core, f"${core}$")
        elif core[:1].isdigit() and tok.startswith("-"):
            tok = f"${tok}$"
        out.append(tok)
    return " ".join(out)


def ci(v: float, lo: float, hi: float, sign: bool = False) -> str:
    f = signed if sign else num
    return f"{f(v)} [{f(lo)}, {f(hi)}]"


def cimac(plain: str) -> str:
    """Turn 'v [lo, hi]' into the \\ci{v}{lo}{hi} macro (layout chosen in main.tex)."""
    v, rest = plain.split(" [", 1)
    lo, hi = rest.rstrip("]").split(", ")
    return "\\ci{" + tex(v) + "}{" + tex(lo) + "}{" + tex(hi) + "}"


def main() -> None:
    GEN.mkdir(parents=True, exist_ok=True)
    manifest = {f["path"]: f["sha256"] for f in json.loads((ROOT / "evidence/import-manifest.json").read_text())["files"]}
    audit = json.loads((ROOT / "evidence/migration-audit.json").read_text())
    members = {m["path"]: m["sha256"] for a in audit["archives"] if a["path"] == ZIPPATH for m in a["members"]}
    raw = (ROOT / ZIPPATH).read_bytes()
    if sha256(raw) != manifest[ZIPPATH]:
        sys.exit("results archive digest mismatch")
    zf = zipfile.ZipFile(io.BytesIO(raw))
    used: dict[str, str] = {}

    def read(name: str) -> dict:
        data = zf.read(PREFIX + name)
        if sha256(data) != members[PREFIX + name]:
            sys.exit(f"member digest mismatch: {name}")
        used[PREFIX + name] = members[PREFIX + name]
        return json.loads(data)

    M = read("run/metrics.json")
    F = read("run/failures.json")
    P = read("run/prepare.json")
    E = read("run/embed.json")
    V = read("run/verify.json")
    RL = read("run/run-log.json")
    CR = read("receipts/clean-room/compare-with-original.json")
    raw_log = zf.read(PREFIX + "run/run-all.log")
    if sha256(raw_log) != members[PREFIX + "run/run-all.log"]:
        sys.exit("member digest mismatch: run/run-all.log")
    used[PREFIX + "run/run-all.log"] = members[PREFIX + "run/run-all.log"]
    import re
    real = float(re.search(r"([0-9.]+) real", raw_log.decode()).group(1))
    mism: list[str] = []

    def check(label: str, got: str, want: str) -> None:
        if got.replace("−", "-") != want.replace("−", "-"):
            mism.append(f"{label}: generated {got!r} != article {want!r}")

    def seed0_seconds(split: str, method: str) -> float:
        return F[split]["cnn_device_parity"][method]["0"]["seconds_this_seed"]

    # ---- Table 2: every method on both splits
    lines = []
    for name in ORDER:
        cells, cmp = [], []
        for split in SPLITS:
            x = M["splits"][split]["methods"][name]
            mse = ci(x["mse"], *x["mse_ci95"])
            r2 = num(x["r2"])
            p = ci(x["precision_at_k"], *x["precision_at_k_ci95"])
            cells += [mse, r2, p]
        times, mem = [], []
        for split in SPLITS:
            x = M["splits"][split]["methods"][name]
            if name in ("cnn", "utrlm_cnn"):
                times.append(f"{seed0_seconds(split, name):.0f}")
            else:
                times.append(f"{x['fit_seconds']:.1f}")
            mem.append(f"{x['peak_rss_mb'] / 1000:.2f}")
        t, m_ = " / ".join(times), " / ".join(mem)
        want = ARTICLE_T2[name]
        for i, got in enumerate(cells + [t, m_]):
            check(f"T2 {name} col{i}", got, want[i])
        texcells = [cimac(c) if "[" in c else tex(c) for c in cells]
        t2 = "\\twoline{" + "}{".join(times) + "}"
        m2 = "\\twoline{" + "}{".join(mem) + "}"
        lines.append(f"{NAMES[name]} & " + " & ".join(texcells) + f" & {t2} & {m2} \\\\")
        if name == "cheap_combined":
            lines.append(r"\midrule")
    (GEN / "tab_methods.tex").write_text("\n".join(lines) + "\n")

    # Appendix: secondary metrics (MAE, Pearson, Spearman, enrichment, validation MSE), incl. replay
    lines = []
    for split in SPLITS:
        for name in ["comp_full_replay"] + ORDER:
            x = M["splits"][split]["methods"][name]
            pe = "--" if x.get("pearson") is None else num(x["pearson"])
            spm = "--" if x.get("spearman") is None else num(x["spearman"])
            lines.append(f"{'random' if split == 'historical' else split} & {NAMES[name]} & {num(x['mae'])} & {pe} & {spm} & {x['enrichment']:.2f} & "
                         f"{num(x['val_mse'])} & {x['coverage']} \\\\")
        if split == "historical":
            lines.append(r"\midrule")
    (GEN / "tab_secondary.tex").write_text("\n".join(lines) + "\n")

    # ---- Table 3: paired comparisons as in the article
    comps = {(c["method"], c["reference"], s): c for s in SPLITS for c in M["splits"][s]["comparisons"]}
    lines = []
    for meth, ref, split, wm, wv, wp, wpv in ARTICLE_T3:
        c = comps[(meth, ref, split)]
        mse = ci(c["mse_reduction"], *c["mse_reduction_ci95"], sign=True)
        pg = ci(c["precision_gain"], *c["precision_gain_ci95"], sign=True)
        v1, v2 = VERDICT[c["mse_verdict"]], VERDICT[c["precision_verdict"]]
        for lab, g, w in (("mse", mse, wm), ("mv", v1, wv), ("p", pg, wp), ("pv", v2, wpv)):
            check(f"T3 {meth}-{ref}-{split} {lab}", g, w)
        label = "random" if split == "historical" else "grouped"
        lines.append(f"{SHORT[meth]} vs {SHORT[ref]} & {label} & {cimac(mse)} & {v1} & {cimac(pg)} & {v2} \\\\")
    (GEN / "tab_comparisons.tex").write_text("\n".join(lines) + "\n")

    # Appendix: all 22 registered comparisons
    lines = []
    for split in SPLITS:
        for c in M["splits"][split]["comparisons"]:
            mse = ci(c["mse_reduction"], *c["mse_reduction_ci95"], sign=True)
            pg = ci(c["precision_gain"], *c["precision_gain_ci95"], sign=True)
            label = "random" if split == "historical" else "grouped"
            lines.append(f"{label} & {SHORT[c['method']]} & {SHORT[c['reference']]} & {cimac(mse)} & "
                         f"{VERDICT[c['mse_verdict']]} & {cimac(pg)} & {VERDICT[c['precision_verdict']]} \\\\")
        if split == "historical":
            lines.append(r"\midrule")
    (GEN / "tab_comparisons_all.tex").write_text("\n".join(lines) + "\n")

    # ---- Per-seed CNN results
    lines = []
    for split in SPLITS:
        for name in ("cnn", "utrlm_cnn"):
            ps = M["splits"][split]["methods"][name]["per_seed"]
            cells = [f"{num(ps[s]['mse'])} / {num(ps[s]['precision_at_k'])}" for s in ("seed0", "seed1", "seed2")]
            secs = [f"{F[split]['cnn_device_parity'][name][s]['seconds_this_seed']:.0f}" for s in ("0", "1", "2")]
            label = "random" if split == "historical" else "grouped"
            lines.append(f"{label} & {SHORT[name]} & " + " & ".join(cells) + f" & {', '.join(secs)} \\\\")
    (GEN / "tab_seeds.tex").write_text("\n".join(lines) + "\n")

    # ---- Device parity (validation MSE on training device vs CPU)
    lines = []
    for split in SPLITS:
        for name in ("cnn", "utrlm_cnn"):
            for s in ("0", "1", "2"):
                d = F[split]["cnn_device_parity"][name][s]
                label = "random" if split == "historical" else "grouped"
                lines.append(f"{label} & {SHORT[name]} & {s} & {d['device']} & {d['val_mse_training_device']:.8f} & "
                             f"{d['val_mse_cpu']:.8f} & {d['abs_diff']:.1e} \\\\")
    (GEN / "tab_parity.tex").write_text("\n".join(lines) + "\n")

    # ---- Table 4: declared examples
    lines = []
    rule = {"measured MRL closest to test 10th percentile": "10th percentile",
            "measured MRL closest to test 50th percentile": "50th percentile",
            "measured MRL closest to test 90th percentile": "90th percentile",
            "largest absolute cnn (seed 0) error": "Largest CNN error",
            "lowest-index snv variant whose reference (mother) is also in test": "SNV variant",
            "reference (mother) of that snv variant": "SNV reference"}
    for ex in M["splits"]["grouped"]["examples"]:
        r = rule.get(ex["rule"], ex["rule"])
        pr = ex["predicted"]
        lib = ex["library"].replace("_", r"\_")
        lines.append(f"{r} & {lib} & {ex['source_index']} & {ex['total_reads']:,} & "
                     f"{ex['measured_mrl']:.2f} & {pr['cheap_combined']:.2f} & {pr['cnn']:.2f} & {pr['utrlm_cnn']:.2f} & "
                     f"{pr['utrlm_pos_ridge']:.2f} \\\\")
        lines.append(f"\\multicolumn{{9}}{{@{{}}l}}{{\\quad insert: \\texttt{{{ex['insert']}}}}} \\\\[2pt]")
    (GEN / "tab_examples.tex").write_text("\n".join(lines) + "\n")
    rules = [e["rule"] for e in M["splits"]["grouped"]["examples"]]

    # ---- Read-depth quartiles
    lines = []
    for split in SPLITS:
        s = M["splits"][split]
        edges = F[split]["read_depth_quartile_edges"]
        label = "random" if split == "historical" else "grouped"
        for i, q in enumerate(s["cnn_mse_by_read_depth_quartile"]):
            lo, hi = edges[i], edges[i + 1]
            lines.append(f"{label} & {q} & {lo:,.0f}--{hi:,.0f} & {num(s['cnn_mse_by_read_depth_quartile'][q])} & "
                         f"{num(s['reference_mse_by_read_depth_quartile'][q])} \\\\")
        if split == "historical":
            lines.append(r"\midrule")
    (GEN / "tab_depth.tex").write_text("\n".join(lines) + "\n")
    g = M["splits"]["grouped"]
    check("depth Q1 cnn", num(g["cnn_mse_by_read_depth_quartile"]["Q1 (fewest reads)"]), "0.785")
    check("depth Q4 cnn", num(g["cnn_mse_by_read_depth_quartile"]["Q4 (most reads)"]), "0.419")
    check("depth Q1 ref", num(g["reference_mse_by_read_depth_quartile"]["Q1 (fewest reads)"]), "1.024")
    check("depth Q4 ref", num(g["reference_mse_by_read_depth_quartile"]["Q4 (most reads)"]), "0.606")

    # ---- Per-sub-library MSE and split composition
    libs = sorted(P["library_counts"])
    lines = []
    for lib in libs:
        row = [lib.replace("_", r"\_"), f"{P['library_counts'][lib]:,}"]
        for split in SPLITS:
            rb = F[split]["records_by_library_and_split"].get(lib, {})
            row.append("/".join(f"{rb.get(k, 0):,}" for k in ("train", "validation", "test")))
            row.append(f"{F[split]['components_per_library'].get(lib, 0):,}")
        lines.append(" & ".join(row) + r" \\")
    (GEN / "tab_composition.tex").write_text("\n".join(lines) + "\n")
    lines = []
    for lib in libs:
        row = [lib.replace("_", r"\_")]
        for split in SPLITS:
            pl = M["splits"][split]["per_library_mse"]
            for name in ("cheap_combined", "cnn", "utrlm_cnn"):
                v = pl[name].get(lib)
                row.append("--" if v is None else num(v))
        lines.append(" & ".join(row) + r" \\")
    (GEN / "tab_perlib.tex").write_text("\n".join(lines) + "\n")
    sw = F["grouped"]["step_worst_allow_uatg"]
    check("family CNN MSE", f"{sw['top_component_cnn_mse']:.2f}", "3.98")
    check("family ref MSE", f"{sw['top_component_ref_mse']:.2f}", "0.59")
    check("family share", f"{100 * sw['share_of_cnn_sse_in_top_component']:.0f}", "82")
    check("sublib cnn", num(M["splits"]["grouped"]["per_library_mse"]["cnn"]["step_worst_to_best_allow_uatg"]), "1.134")
    check("sublib ref", num(M["splits"]["grouped"]["per_library_mse"]["cheap_combined"]["step_worst_to_best_allow_uatg"]), "0.405")
    check("rand sublib cnn", num(M["splits"]["historical"]["per_library_mse"]["cnn"]["step_worst_to_best_allow_uatg"]), "0.314")
    check("rand sublib ref", num(M["splits"]["historical"]["per_library_mse"]["cheap_combined"]["step_worst_to_best_allow_uatg"]), "0.723")

    # ---- Run timing (per step)
    agg: dict[str, float] = {}
    for st in RL["steps"]:
        a = st["args"]
        key = a[0] if a[0] != "fit" else f"fit {a[a.index('--split') + 1]} {a[a.index('--method') + 1]}"
        agg[key] = agg.get(key, 0.0) + st["wall_seconds"]
    lines = []
    for k, v in agg.items():
        if k.startswith("fit "):
            _, split, meth = k.split(" ")
            label = ("random" if split == "historical" else "grouped") + ": " + NAMES.get(meth, meth)
            label = label.replace(" (seed 0)", " (3 seeds)")
        else:
            label = k
        lines.append(f"{label} & {v:,.1f} \\\\")
    total = sum(agg.values())
    (GEN / "tab_runlog.tex").write_text("\n".join(lines) + "\n")

    # ---- Clean-room comparison
    lines = []
    for k, v in CR.items():
        if isinstance(v, dict) and "max_abs_pred_diff" in v:
            split, meth = k.split("/")
            label = "random" if split == "historical" else "grouped"
            lines.append(f"{label} & {NAMES.get(meth, meth).replace(' (seed 0)', '')} & {v['orig_test_mse']:.6f} & "
                         f"{v['clean_test_mse']:.6f} & {v['max_abs_pred_diff']:g} \\\\")
    (GEN / "tab_cleanroom.tex").write_text("\n".join(lines) + "\n")

    # ---- Verification checks
    def esc(t: str) -> str:
        t = t.replace("_", chr(92) + "_")
        return t if len(t) < 60 else t[:16] + chr(92) + "ldots{}"
    lines = [f"{esc(c['check'])} & {'passed' if c['passed'] else 'FAILED'} & {esc(c['detail'])} \\\\"
             for c in V["checks"]]
    (GEN / "tab_verify.tex").write_text("\n".join(lines) + "\n")

    # ---- Macros
    dep = M["dependence"]
    lc = F["largest_component"]
    sc = P["split_counts_full"]
    mac = {
        "Records": f"{P['checks']['rows']:,}", "Components": f"{dep['components']:,}", "MotherFamilies": f"{dep['mother_families']:,}",
        "OverlapShare": f"{100 * dep['historical_test_with_component_in_train']:.1f}",
        "ICC": f"{dep['icc_training_labels_historical']['icc1']:.3f}",
        "LargestComponent": f"{lc['records']:,}", "LargestShare": f"{100 * lc['share_of_all_records']:.1f}",
        "LargestMean": f"{lc['mrl_mean_sd'][0]:.2f}", "AllMean": f"{lc['all_records_mrl_mean_sd'][0]:.2f}",
        "RandTrain": f"{sc['historical']['train']:,}", "RandVal": f"{sc['historical']['validation']:,}", "RandTest": f"{sc['historical']['test']:,}",
        "GrpTrain": f"{sc['grouped']['train']:,}", "GrpVal": f"{sc['grouped']['validation']:,}", "GrpTest": f"{sc['grouped']['test']:,}",
        "RandBase": f"{M['splits']['historical']['test_base_rate']:.3f}", "GrpBase": f"{M['splits']['grouped']['test_base_rate']:.3f}",
        "RandCut": f"{M['splits']['historical']['high_mrl_cutoff']:.3f}", "GrpCut": f"{M['splits']['grouped']['high_mrl_cutoff']:.3f}",
        "RandComponents": f"{M['splits']['historical']['test_components']:,}", "GrpComponents": f"{M['splits']['grouped']['test_components']:,}",
        "Boot": f"{M['bootstraps']:,}", "BootSeed": str(M["bootstrap_seed"]),
        "EmbedSeconds": f"{E['embed_seconds']:.1f}", "EmbedRSS": f"{E['peak_rss_mb'] / 1000:.2f}",
        "MLMAcc": f"{E['mlm_masked_accuracy']:.3f}", "MajorityBase": f"{E['majority_base_rate']:.3f}",
        "UTRLMParams": f"{E['parameters']:,}", "PosCacheGB": f"{E['cache_bytes']['utrlm_pos.f16.npy'] / 1e9:.2f}",
        "RunSeconds": f"{real:,.0f}", "RunMinutes": f"{real / 60:.1f}", "StepSeconds": f"{total:,.1f}",
        "ErrOverTwo": str(F["grouped"]["cnn_abs_error_over_2_mrl"]), "ErrOverTwoReads": f"{F['grouped']['cnn_abs_error_over_2_median_reads']:.0f}",
        "MedianReads": f"{F['grouped']['median_reads_all_test']:.0f}",
    }
    check("overlap", mac["OverlapShare"], "79.3")
    check("icc", mac["ICC"], "0.495")
    check("components", mac["Components"], "33,575")
    check("largest", mac["LargestComponent"], "14,101")
    check("largest share", mac["LargestShare"], "14.1")
    check("largest mean", mac["LargestMean"], "6.59")
    check("all mean", mac["AllMean"], "5.74")
    check("rand base", mac["RandBase"], "0.095")
    check("grp base", mac["GrpBase"], "0.055")
    check("grp cut", mac["GrpCut"], "7.402")
    check("embed s", mac["EmbedSeconds"], "134.8")
    check("embed rss", mac["EmbedRSS"], "1.76")
    check("mlm", mac["MLMAcc"], "0.416")
    check("majority", mac["MajorityBase"], "0.329")
    check("run seconds", mac["RunSeconds"], "3,417")
    check("err>2", mac["ErrOverTwo"], "289")
    check("err>2 reads", mac["ErrOverTwoReads"], "485")
    check("median reads", mac["MedianReads"], "616")
    check("pos cache", mac["PosCacheGB"], "1.28")
    if rules[:3] != ["measured MRL closest to test 10th percentile", "measured MRL closest to test 50th percentile",
                     "measured MRL closest to test 90th percentile"]:
        mism.append(f"example rules {rules}")
    (GEN / "macros.tex").write_text("".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in mac.items()))

    receipt = {
        "schema_version": 1,
        "kind": "formatting/extraction only; no recomputation",
        "archive": ZIPPATH, "archive_sha256": manifest[ZIPPATH],
        "members_read_in_memory": used,
        "cross_check_against_article_values": "Table 2 (all cells), Table 3 (all cells and verdicts), read-depth and family numbers, dependence and resource macros",
        "cross_check_mismatches": mism,
        "generated": sorted(p.name for p in GEN.glob("*.tex")),
    }
    (GEN / "extraction-receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    if mism:
        print("\n".join(mism))
        sys.exit("generated tables disagree with the article's reported values")
    print(f"extracted {len(used)} archive members; {len(receipt['generated'])} generated files; 0 mismatches")


if __name__ == "__main__":
    main()
