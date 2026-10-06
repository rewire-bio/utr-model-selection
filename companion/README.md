# utr-baselines

Companion code for the rewire.it article on choosing a model for 5′UTR translation experiments. It compares cheap ridge baselines, a small supervised CNN and a frozen UTR-LM representation for predicting mean ribosome load (MRL) on the Sample et al. (2019) designed 5′UTR library, under the protocol fixed in [`PROTOCOL.md`](PROTOCOL.md) before any new method was scored on a test set.

Everything here is original code. Data and model weights are downloaded at runtime from pinned URLs and checked against SHA-256 hashes; see [`NOTICE.md`](NOTICE.md).

## What it runs

| Step | Command | What happens |
|---|---|---|
| fetch | `utr_baselines.py fetch` | 15 files (32.1 MB): the pinned mRNABench parquet, the GEO designed-library CSV, the UTR-LM checkpoint and UTR-LM's modified ESM code. Every file is hash-checked. |
| prepare | `utr_baselines.py prepare` | Checks that all 100,017 processed sequences share the 25-nt leader and the 780-nt eGFP tail, joins GEO metadata one to one (`rl` must equal the target exactly), rebuilds the historical seed-2541 split and checks its published hash, and builds the grouped split. |
| embed | `utr_baselines.py embed` | Frozen UTR-LM (`ESM2_1.4_five_species`, 1.21 M parameters) on CPU. A masked-nucleotide check must beat the majority-base rate first. |
| fit | `utr_baselines.py fit --split S --method M` | One method on one split, in its own process. Saves validation and test predictions and a `fit.json` with time, peak memory, alpha or epochs. |
| evaluate | `utr_baselines.py evaluate` | MSE, MAE, R², correlations (null for constant predictions), precision at 1% capacity, 2,000 cluster-bootstrap resamples, paired comparisons and the pre-registered verdicts, per-sub-library and per-read-depth error, and examples chosen by the declared rule. |
| run-all | `utr_baselines.py run-all` | All of the above in order. |
| verify | `verify.py` | Independent check with no shared code: split hash, grouped components by a separate breadth-first search, every test metric recomputed from saved predictions and source labels, the replay MSE against the published value, and a scikit-learn refit of one ridge baseline. |
| figures | `make_figures.py` | The three charts, from `metrics.json` only. |
| failures | `describe_failures.py` | Descriptive follow-up (components per sub-library, read-depth edges, the concentrated CNN failure). Fits nothing. |

## Setup

Requires [uv](https://docs.astral.sh/uv/) and about 3 GB of free disk (0.85 GB environment, 31 MB inputs, 1.3 GB embedding cache for a full run).

```bash
cd utr-baselines
uv sync --extra test            # Python 3.11, numpy 1.26.4, scikit-learn 1.5.2, torch 2.4.1 (locked in uv.lock)
uv run pytest -q                # 10 passed, 1 skipped (the full-run test needs UTR_WORK)
```

## Smoke run (installation check, about 3–7 minutes)

Every 20th record (5,001), two CNN epochs, seed 0. Its numbers are not evidence. Measured on the test machine: 213 s with MPS for CNN training (sum of step times), 199 s in the clean-environment rerun, 405 s when the final archive was checked on the same, busier machine, and 190 s with `--cpu-only` and `OMP_NUM_THREADS=4` (an independent check by the parent session; all 22 method-split results completed, the four smoke CNN fits recorded `device=cpu`, and `verify.py` passed).

```bash
uv run python utr_baselines.py run-all --inputs runs/inputs --work runs/smoke --smoke
uv run python verify.py --inputs runs/inputs --work runs/smoke        # ends with ALL PASSED
```

## Full run (about 57 minutes on an Apple M4)

```bash
uv run python utr_baselines.py run-all --inputs runs/inputs --work runs/full
uv run python verify.py --inputs runs/inputs --work runs/full         # ends with ALL PASSED
UTR_WORK=runs/full uv run pytest -q                                   # 11 passed
uv run python make_figures.py --work runs/full --out runs/full/figures
uv run python describe_failures.py --work runs/full
```

Add `--cpu-only` to `run-all` or `fit` to keep CNN training off Apple MPS. The smoke configuration was checked this way. A full CPU-only run was not: in a pre-registration probe on the test machine, one full-data epoch took 151 s on CPU (4 threads) against 11 s on MPS, so expect several hours. Whether seeded CPU training repeats exactly was not tested.

The tutorial notebook `tutorial.ipynb` drives the same CLI (smoke configuration by default): `uv sync --extra notebook`, then open it in Jupyter or run it with `nbclient`. Executed on the test machine it took 230 s, using MPS for the smoke CNN fits.

## Measured on the test machine

Apple M4 (10 cores), 16 GB RAM, macOS 26.6.2, Python 3.11.13, torch 2.4.1, 30 September 2026. Each step runs in its own process, so times and peak memory are per step. Times exclude installation. The laptop was shared: other work was running and it was swapping (about 7 GB) during the grouped fits. These are receipts from one run, not a controlled benchmark; do not read small differences as stable speed rankings. CNN rows cover all three seeds (one seed took 174–313 s); ridge rows include the validation alpha search.

| Step | Wall time | Peak RSS |
|---|---:|---:|
| fetch (15 files, 32.1 MB) | first run a few seconds; cached 0.5 s | – |
| prepare | 3.6 s | 0.96 GB |
| UTR-LM embedding, 100,017 inserts, CPU | 137.5 s (134.8 s embedding) | 1.76 GB |
| cheap ridge baselines, per split | 0.6–21.3 s | 0.27–0.55 GB |
| CNN, 3 seeds, per split | 589–735 s | 1.2–1.3 GB |
| UTR-LM per-position + ridge, per split | 90–107 s | 2.7–3.2 GB |
| UTR-LM + CNN head, 3 seeds, per split | 778–877 s | 2.2 GB |
| evaluate | 17.5 s | – |
| **whole run** | **3,417 s** | **3.2 GB (largest step)** |

Embedding cache: 1.28 GB for per-position float16 embeddings plus 51 MB for mean-pooled embeddings.

## Results (from `runs/full/metrics.json`)

Test MSE in MRL² with 95% cluster-bootstrap intervals; R² is the coefficient of determination (1 − SSE/SST), not a squared correlation. Precision at k = 150 (1% of test records) for "high-MRL" (at or above the 90th percentile of that split's training labels); in bootstrap draws the capacity is 1% of the resampled list (see `PROTOCOL.md`, clarification 5). The training-mean precision is an artefact of the source-index tie rule; its chance expectation is the test high-MRL share, 0.095 (historical) and 0.055 (grouped). All results are exploratory. The grouped test set excludes the 14,101-record component forced into training (see `PROTOCOL.md`, clarification 4).

| Method | Historical MSE | Historical R² | Historical P@150 | Grouped MSE | Grouped R² | Grouped P@150 |
|---|---:|---:|---:|---:|---:|---:|
| training mean | 2.366 [2.234, 2.481] | −0.000 | 0.053 | 2.224 [2.096, 2.384] | −0.022 | 0.040 |
| composition, full sequence (replay) | 1.914 [1.834, 2.004] | 0.190 | 0.327 | 1.888 [1.807, 1.975] | 0.132 | 0.233 |
| composition, insert | 1.914 [1.834, 2.004] | 0.190 | 0.327 | 1.888 [1.807, 1.975] | 0.132 | 0.233 |
| 1–3-mer counts | 1.225 [1.177, 1.267] | 0.482 | 0.533 | 1.162 [1.111, 1.210] | 0.466 | 0.540 |
| positional one-hot | 1.769 [1.709, 1.839] | 0.252 | 0.360 | 1.767 [1.702, 1.836] | 0.188 | 0.360 |
| uAUG/Kozak features | 1.280 [1.228, 1.326] | 0.459 | 0.340 | 1.193 [1.138, 1.248] | 0.452 | 0.307 |
| cheap combined (reference) | 0.849 [0.808, 0.888] | 0.641 | 0.580 | 0.776 [0.739, 0.814] | 0.643 | 0.553 |
| CNN, one-hot (seed 0) | 0.427 [0.389, 0.465] | 0.819 | 0.787 | 0.560 [0.529, 0.595] | 0.743 | 0.573 |
| UTR-LM mean + ridge | 1.184 [1.143, 1.222] | 0.499 | 0.460 | 1.139 [1.093, 1.183] | 0.477 | 0.347 |
| UTR-LM per-position + ridge | 0.939 [0.904, 0.981] | 0.603 | 0.513 | 1.020 [0.981, 1.061] | 0.531 | 0.380 |
| UTR-LM + CNN head (seed 0) | 0.407 [0.376, 0.440] | 0.828 | 0.660 | 0.570 [0.539, 0.602] | 0.738 | 0.567 |

CNN seed ranges (test MSE): historical one-hot 0.413–0.439, UTR-LM input 0.407–0.412; grouped one-hot 0.559–0.570, UTR-LM input 0.538–0.570.

## Expected reproduction tolerances

- `prepare`, the replay, every ridge method and the CPU UTR-LM embeddings were reproduced exactly by the clean-environment rerun on the same machine (maximum prediction difference 0.0; embeddings identical). Other platforms were not tested. `verify.py` compares an independent scikit-learn refit of one ridge baseline at a tolerance of 1e-6 (observed 1.4e-7).
- CNN training used Apple MPS. In the clean-environment rerun on the same machine, the grouped-split seed-0 CNN reproduced its test predictions exactly (maximum difference 0.0). Other machines, operating systems and torch versions were not tested, so no cross-platform tolerance is established. If a rerun elsewhere falls well outside the seed ranges above, treat that as a reason to investigate, not as an expected tolerance. Precision at 150 varies more between seeds: 0.713–0.787 (historical CNN) and 0.533–0.580 (grouped CNN).
- The replay reproduces the published rewire-benchmarks historical MSE (1.914439715839851) within 1e-9.

## Results archive

`utr-baselines-results.zip` holds the evidence from the run described here (metrics, per-fit receipts, predictions, verification and device receipts), with a `MANIFEST.md`. It contains no source datasets, model weights or embedding caches.

## Scope

One reporter library, one cell line and one assay. A random split and a grouped split of the same library. The frozen checkpoint was not fine-tuned. Nothing here measures protein output, other reporters or endogenous mRNAs. See the article for the full limits.

## Artifact safety (October 2026 maintenance)

Use a fresh work directory for each run. `prepare`, `run-all`, `embed` and individual
fits refuse to overwrite existing stage outputs. New embedding receipts bind the
cache bytes to the exact prepared record file; fit receipts bind predictions to
that same file. A changed or reordered record file requires a fresh embedding run.

`evaluate` requires all eleven methods on both splits and complete, finite
validation/test predictions, including every saved seed column. Historical
receipts lack these new hashes; inspecting an intact historical work directory
requires `evaluate --allow-legacy-artifacts --work PATH`. That explicit compatibility
option retains population, completeness and finite-value validation, but cannot
retroactively establish cache provenance. It must not be used to bypass a mismatch
in a new run. The downloadable historical archives are unchanged.

`verify.py` independently checks source checksums, declared full/smoke population,
source labels/inserts, all registered methods and finite metric discrepancies.
The full-run check also reconstructs the deterministic grouped allocation.
The historical ten-test count above describes the original run; `make test` at
the repository root runs the expanded maintained regression suite.
