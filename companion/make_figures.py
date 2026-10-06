"""Figures from a finished run's metrics.json (no other inputs).

    python make_figures.py --work runs/full --out figures
"""

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

CHEAP, CNN, FROZEN = "#1baf7a", "#2a78d6", "#eb6834"  # validated palette slots 3, 1, 2
INK, MUTED, GRID = "#0b0b0b", "#52514e", "#e4e3df"
LABELS = {
    "train_mean": "training mean", "comp_full_replay": "composition, full seq. (replay)",
    "comp_utr": "composition", "kmer_utr": "1-3-mer counts", "onehot_pos": "positional one-hot",
    "annot": "uAUG/Kozak features", "cheap_combined": "cheap combined", "cnn": "CNN (one-hot)",
    "utrlm_mean_ridge": "UTR-LM mean + ridge", "utrlm_pos_ridge": "UTR-LM per-position + ridge",
    "utrlm_cnn": "UTR-LM + CNN head",
}
FAMILY = {m: CHEAP for m in ["comp_utr", "kmer_utr", "onehot_pos", "annot", "cheap_combined"]}
FAMILY.update({"cnn": CNN, "utrlm_mean_ridge": FROZEN, "utrlm_pos_ridge": FROZEN, "utrlm_cnn": FROZEN})
MARKER = {"comp_utr": "o", "kmer_utr": "s", "onehot_pos": "D", "annot": "^", "cheap_combined": "h",
          "cnn": "o", "utrlm_mean_ridge": "o", "utrlm_pos_ridge": "s", "utrlm_cnn": "D"}
OFFSET = {  # label offsets in points (dx, dy, horizontal alignment)
    "cnn": (-8, -14, "right"), "utrlm_cnn": (8, 6, "left"), "annot": (0, 10, "center"),
    "kmer_utr": (0, -16, "center"), "utrlm_mean_ridge": (0, 9, "center"), "cheap_combined": (-8, -13, "right"),
}
SPLIT_TITLE = {"historical": "Historical random split (replay)", "grouped": "Grouped split (new)"}


def style(ax):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(MUTED)
    ax.tick_params(colors=MUTED, labelsize=9)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def cost_seconds(work, split, m, embed_seconds):
    """Wall time to produce the plotted model: seed 0 for CNN heads (the plotted MSE is seed 0), the whole
    fit for ridge methods (including the validation alpha grid), plus the one-off embedding pass for UTR-LM."""
    fit = json.loads((work / "runs" / split / m / "fit.json").read_text())
    t = fit["seeds"]["0"]["seconds"] if "seeds" in fit else fit["seconds"]
    return t + (embed_seconds if m.startswith("utrlm") else 0.0)


def fig_accuracy_cost(metrics, work, out):
    emb = metrics["embed"]["embed_seconds"] + metrics["embed"]["load_seconds"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharey=True)
    for ax, split in zip(axes, ["historical", "grouped"]):
        s = metrics["splits"][split]
        for m, v in s["methods"].items():
            if m not in FAMILY:
                continue
            x = cost_seconds(work, split, m, emb)
            lo, hi = v["mse_ci95"]
            ax.errorbar(x, v["mse"], yerr=[[v["mse"] - lo], [hi - v["mse"]]], fmt=MARKER[m], ms=8,
                        color=FAMILY[m], mec="white", mew=1.2, elinewidth=2, capsize=0, zorder=3)
            dx, dy, ha = OFFSET.get(m, (7, 3, "left"))
            ax.annotate(LABELS[m], (x, v["mse"]), xytext=(dx, dy), textcoords="offset points", fontsize=8.5,
                        color=INK, ha=ha)
        base = s["methods"]["train_mean"]["mse"]
        ax.axhline(base, color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.annotate("training mean", (0.06, base), xytext=(0, 3),
                    textcoords="offset points", fontsize=8.5, color=MUTED)
        ax.set_xscale("log")
        ax.set_xlim(0.05, 5000)
        ax.set_title(SPLIT_TITLE[split], fontsize=11, color=INK, loc="left")

        style(ax)
    axes[0].set_ylabel("test MSE, MRL² (lower is better)", fontsize=9, color=MUTED)
    axes[0].set_ylim(0, None)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, ms=8, label=l) for c, l in
               [(CHEAP, "cheap ridge baselines"), (CNN, "supervised CNN"), (FROZEN, "frozen UTR-LM")]]
    fig.legend(handles=handles, loc="upper center", ncol=3, frameon=False, fontsize=9)
    fig.supxlabel("wall time to fit the plotted model on one shared laptop, s (log scale; CNN = seed 0; ridge includes "
                  "features and alpha search; UTR-LM adds the one-off embedding pass)", fontsize=9, color=MUTED)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(out / "fig-accuracy-vs-cost.png", dpi=200)
    fig.savefig(out / "fig-accuracy-vs-cost.svg")
    plt.close(fig)


def fig_paired(metrics, out):
    thr = metrics["thresholds"]["mse"]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6), sharex=True, sharey=True)
    for ax, split in zip(axes, ["historical", "grouped"]):
        s = metrics["splits"][split]
        rows = [c for c in s["comparisons"] if c["reference"] == s["reference"]
                and c["method"] in ("cnn", "utrlm_mean_ridge", "utrlm_pos_ridge", "utrlm_cnn")]
        n_ref = len(rows)
        rows += [c for c in s["comparisons"] if c["reference"] == "cnn"]
        for i, c in enumerate(rows):
            y = len(rows) - 1 - i
            lo, hi = c["mse_reduction_ci95"]
            ax.plot([lo, hi], [y, y], color=FAMILY[c["method"]], lw=2.5, solid_capstyle="round")
            ax.plot(c["mse_reduction"], y, MARKER[c["method"]], color=FAMILY[c["method"]], ms=8, mec="white", mew=1.2)
        ax.set_yticks(range(len(rows)))
        ax.set_yticklabels([f"{LABELS[c['method']]}\nvs {LABELS[c['reference']]}" for c in rows][::-1], fontsize=8)
        ax.axhline(len(rows) - n_ref - 0.5, color=MUTED, lw=0.8)
        ax.axvline(0, color=MUTED, lw=1)
        ax.axvline(thr, color=MUTED, lw=1, ls=(0, (4, 3)))
        ax.annotate(f"practical\nthreshold +{thr:.2f}", (thr, -0.9), xytext=(4, 0), textcoords="offset points",
                    fontsize=8, color=MUTED, va="bottom")
        ax.set_ylim(-1, len(rows) - 0.4)
        ax.set_title(SPLIT_TITLE[split], fontsize=11, color=INK, loc="left")
        style(ax)
    fig.supxlabel("MSE reduction against the reference, MRL² (positive = better than the reference); 95% cluster-bootstrap interval",
                  fontsize=9, color=MUTED)
    fig.tight_layout()
    fig.savefig(out / "fig-paired-differences.png", dpi=200)
    fig.savefig(out / "fig-paired-differences.svg")
    plt.close(fig)


def fig_failures(metrics, out):
    s = metrics["splits"]["grouped"]
    ref = s["reference"]
    methods = [m for m in (ref, "cnn", "utrlm_cnn") if m in s["per_library_mse"]]
    counts = s["library_test_counts"]
    libs = sorted([l for l in counts if counts[l] >= 100], key=lambda l: s["per_library_mse"]["cnn"][l])
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.8), gridspec_kw={"width_ratios": [1.6, 1]})
    ax = axes[0]
    h = 0.26
    for j, m in enumerate(methods):
        vals = [s["per_library_mse"][m][l] for l in libs]
        ax.barh([i - (j - 1) * (h + 0.02) for i in range(len(libs))], vals, height=h, color=FAMILY[m],
                label=LABELS[m])
    ax.set_yticks(range(len(libs)))
    ax.set_yticklabels([f"{l} (n={counts[l]:,})" for l in libs], fontsize=8)
    ax.set_xlabel("test MSE, MRL² (grouped split)", fontsize=9, color=MUTED)
    ax.set_title("Error by sub-library", fontsize=11, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8, loc="lower right")
    style(ax)
    ax = axes[1]
    q = list(s["cnn_mse_by_read_depth_quartile"])
    for j, (m, key) in enumerate([(ref, "reference_mse_by_read_depth_quartile"), ("cnn", "cnn_mse_by_read_depth_quartile")]):
        vals = [s[key][k] for k in q]
        ax.bar([i + (j - 0.5) * 0.4 for i in range(len(q))], vals, width=0.38, color=FAMILY[m], label=LABELS[m])
    ax.set_xticks(range(len(q)))
    ax.set_xticklabels([k.replace(" (", "\n(") for k in q], fontsize=8)
    ax.set_ylabel("test MSE, MRL²", fontsize=9, color=MUTED)
    ax.set_title("Error by sequencing depth", fontsize=11, color=INK, loc="left")
    ax.legend(frameon=False, fontsize=8)
    style(ax)
    fig.tight_layout()
    fig.savefig(out / "fig-error-by-library-and-depth.png", dpi=200)
    fig.savefig(out / "fig-error-by-library-and-depth.svg")
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    metrics = json.loads((args.work / "metrics.json").read_text())
    fig_accuracy_cost(metrics, args.work, args.out)
    fig_paired(metrics, args.out)
    fig_failures(metrics, args.out)
    print("figures written to", args.out)


if __name__ == "__main__":
    main()
