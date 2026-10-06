"""Write tutorial.ipynb. The notebook drives the same CLI as the article and reads its outputs."""

import json
from pathlib import Path

cells = [
    ("markdown", """# UTR model choice: a real-data walkthrough

This notebook runs the companion CLI (`utr_baselines.py`) on real data and reads its outputs. By default it runs the
**smoke** configuration (every 20th record, 2 CNN epochs, seed 0), which proves the installation works; its numbers are
not evidence. On the test machine (Apple M4) this notebook took 230 s, using Apple MPS for the smoke CNN fits; a CPU-only
smoke run (`--cpu-only`) took 190 s. Set `SMOKE = False` to run the full comparison (57 minutes on that machine with MPS;
see README)."""),
    ("code", """import json, subprocess, sys
from pathlib import Path
import pandas as pd

SMOKE = True
INPUTS = Path("runs/inputs")
WORK = Path("runs/smoke" if SMOKE else "runs/full")"""),
    ("markdown", "## 1. Download pinned inputs, prepare, embed, fit and evaluate\n`run-all` checks every SHA-256 before use and runs each fit in its own process so peak memory is per method."),
    ("code", """if not (WORK / "metrics.json").exists():
    cmd = [sys.executable, "utr_baselines.py", "run-all", "--inputs", str(INPUTS), "--work", str(WORK)]
    subprocess.run(cmd + (["--smoke"] if SMOKE else []), check=True)
metrics = json.loads((WORK / "metrics.json").read_text())"""),
    ("markdown", "## 2. What the preparation step checked\nThe 50-nt insert is the only variable part of each 855-nt processed sequence; the GEO metadata join must be exact."),
    ("code", """prep = json.loads((WORK / "prepare.json").read_text())
{k: prep["checks"][k] for k in ["rows", "leader_constant", "tail_constant", "tail_length", "geo_rl_max_abs_diff", "historical_split_sha256"]}"""),
    ("code", """prep["dependence"]"""),
    ("markdown", "## 3. Test metrics on both splits\nMAE is in MRL units (mean ribosomes per mRNA); MSE is in MRL². R² is the coefficient of determination. Correlations are `None` for the constant training-mean predictor, whose precision reflects the source-index tie rule rather than chance (chance is the test high-MRL share)."),
    ("code", """rows = []
for split, s in metrics["splits"].items():
    for m, v in s["methods"].items():
        rows.append({"split": split, "method": m, "MSE": v["mse"], "MSE 95% CI": v["mse_ci95"], "R2": v["r2"],
                     "Spearman": v["spearman"], "P@1%": v["precision_at_k"], "coverage": v["coverage"]})
pd.DataFrame(rows).round(3)"""),
    ("markdown", "## 4. Paired comparisons and the pre-registered verdicts"),
    ("code", """pd.DataFrame([{**c, "split": split} for split, s in metrics["splits"].items() for c in s["comparisons"]])[
    ["split", "method", "reference", "mse_reduction", "mse_reduction_ci95", "mse_verdict", "precision_gain", "precision_verdict"]].round(3)"""),
    ("markdown", "## 5. Examples chosen by the declared rule (grouped test set)\nThe rule picks MRL percentiles, the largest CNN error, and an SNV variant with its reference, not favourable residuals."),
    ("code", """pd.DataFrame(metrics["splits"]["grouped"].get("examples", []))"""),
    ("markdown", "## 6. Independent check and figures"),
    ("code", """subprocess.run([sys.executable, "verify.py", "--inputs", str(INPUTS), "--work", str(WORK)], check=True)
subprocess.run([sys.executable, "make_figures.py", "--work", str(WORK), "--out", str(WORK / "figures")], check=True)
sorted(p.name for p in (WORK / "figures").glob("*.png"))"""),
]

nb = {"cells": [], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
                                "language_info": {"name": "python"}}, "nbformat": 4, "nbformat_minor": 5}
for i, (kind, src) in enumerate(cells):
    cell = {"cell_type": kind, "id": f"c{i:02d}", "metadata": {}, "source": src.splitlines(keepends=True)}
    if kind == "code":
        cell.update(execution_count=None, outputs=[])
    nb["cells"].append(cell)
Path("tutorial.ipynb").write_text(json.dumps(nb, indent=1) + "\n")
print("wrote tutorial.ipynb")
