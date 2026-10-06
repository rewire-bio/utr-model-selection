#!/usr/bin/env python3
"""Write evidence/paper-migration/claims-ledger.json for the imported-evidence manuscript.

Each substantive manuscript claim is tied to a historical artifact path, a pointer inside it and the
artifact's SHA-256 (archive members use the digests recorded in evidence/migration-audit.json;
repository files use the import manifest or are hashed here). No value is computed. Standard library only.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIPNAME = "downloads/utr-baselines-results.zip"
PREFIX = "utr-baselines-results/"
AUDIT = json.loads((ROOT / "evidence/migration-audit.json").read_text())
MEMBERS = {m["path"]: m["sha256"] for a in AUDIT["archives"] if a["path"] == ZIPNAME for m in a["members"]}
MANIFEST = {f["path"]: f["sha256"] for f in json.loads((ROOT / "evidence/import-manifest.json").read_text())["files"]}
PUBLISHED = "article/published-original.md"


def file_sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def member(name: str, pointer: str) -> dict:
    return {"artifact": f"{ZIPNAME}!{PREFIX}{name}", "pointer": pointer, "sha256": MEMBERS[PREFIX + name],
            "container_sha256": MANIFEST[ZIPNAME]}


def article(pointer: str) -> dict:
    return {"artifact": PUBLISHED, "pointer": pointer, "sha256": file_sha(PUBLISHED),
            "note": "byte-identical copy of the published article; link-adjusted copy at article/original.md"}


def repo(path: str, pointer: str) -> dict:
    return {"artifact": path, "pointer": pointer, "sha256": MANIFEST.get(path) or file_sha(path)}


CLAIMS = [
    ("DATA", "100,017 designed records; constant 25-nt leader and 780-nt tail; exact GEO join; split counts 70,011/15,003/15,003 and 69,996/15,017/15,004",
     "sec:data, sec:splits", "companion_computed", [member("run/prepare.json", "$.checks, $.split_counts_full, $.library_counts")]),
    ("LIBRARY", "Library composition: 35,212 human 5'UTR fragments, 3,577 ClinVar variants, 80 trajectories / 7,526 UTRs; two undocumented labels; single measurement; chemistry not stated",
     "sec:data", "literature + article text", [article("section 'The assay measures ribosome loading...'")]),
    ("REPLAY", "Full-sequence composition replay matches insert-only (max diff < 0.001 MRL; MSE 1.914) and the published rewire-benchmarks MSE 1.914439715839851",
     "sec:data, tab:verify", "companion_computed", [member("run/verify.json", "$.checks[4]"), member("run/metrics.json", "$.splits.*.methods.comp_full_replay")]),
    ("DEPENDENCE", "33,575 families; 79.3% of random-split test records have a relative in training; ICC 0.495; largest family 14,101 records (14.1%), mean MRL 6.59 vs 5.74",
     "sec:splits", "companion_computed", [member("run/metrics.json", "$.dependence"), member("run/failures.json", "$.largest_component")]),
    ("BASE-RATES", "High-MRL cut-offs 7.402 (grouped) and 7.360 (random); test base rates 0.055 and 0.095",
     "sec:metrics", "companion_computed", [member("run/metrics.json", "$.splits.*.high_mrl_cutoff, test_base_rate")]),
    ("T2", "Every method on both splits: MSE [CI], R2, P@150 [CI], fit time, peak memory", "tab:methods",
     "companion_computed", [member("run/metrics.json", "$.splits.*.methods.*"), member("run/failures.json", "$.*.cnn_device_parity.*.0.seconds_this_seed")]),
    ("T3", "Paired differences and prespecified verdicts (10 headline comparisons; 22 in appendix)", "tab:comparisons, tab:comparisons-all",
     "companion_computed", [member("run/metrics.json", "$.splits.*.comparisons")]),
    ("HEADLINE-COUNTS", "Top-150 counts: grouped CNN 86 vs cheap 83; random 118 vs 87 (precision x 150)", "sec:main, abstract",
     "companion_computed", [member("run/metrics.json", "$.splits.*.methods.{cnn,cheap_combined}.precision_at_k")]),
    ("SEEDS", "Seed ranges: grouped CNN MSE 0.559-0.570, P@150 0.533-0.580; UTR-LM CNN 0.538-0.570", "tab:seeds, sec:main",
     "companion_computed", [member("run/metrics.json", "$.splits.*.methods.{cnn,utrlm_cnn}.per_seed")]),
    ("EMBED", "UTR-LM checkpoint, 1,208,043 parameters, MLM accuracy 0.416 vs majority 0.329, 134.8 s embedding, 1.76 GB peak, 1.28 GB cache",
     "sec:models, sec:cost", "companion_computed", [member("run/embed.json", "whole file")]),
    ("DEVICE", "UTR-LM MPS vs CPU: max abs diff 7.6 on 64 inserts; MLM 0.412 vs 0.335; CNN validation MSE parity within ~3e-8 for 12 fits",
     "sec:device, tab:parity", "companion_computed", [member("receipts/mps-vs-cpu-utrlm-receipt.txt", "lines 3-5"), member("run/failures.json", "$.*.cnn_device_parity")]),
    ("COST", "Whole run 3,417 s; per-step times; ridge 15-21 s; CNN seeds 174-313 s; three-seed totals 588/733 and 876/777 s; CPU epoch 151 s vs MPS 11 s",
     "sec:cost, tab:runlog", "companion_computed", [member("run/run-all.log", "final /usr/bin/time block"), member("run/run-log.json", "$.steps"), member("run/metrics.json", "$.splits.*.methods.*.fit_seconds"), article("section 'Accuracy cost minutes and gigabytes' (CPU epoch probe)")]),
    ("T4", "Declared examples: six grouped-test records with measured MRL and four predictions", "tab:examples",
     "companion_computed", [member("run/metrics.json", "$.splits.grouped.examples")]),
    ("EXAMPLE-NOTES", "Sequence features of the examples (ATG positions, Kozak ACC, C>T at position 24) and the SNV change analysis",
     "sec:examples", "article text (derived from the inserts in tab:examples)", [article("section 'Six declared examples...'")]),
    ("DEPTH", "Read-depth quartile MSE (grouped CNN 0.785 vs 0.419; reference 1.024 vs 0.606); 289 errors > 2 MRL with median 485 reads vs 616",
     "sec:errors, tab:depth", "companion_computed", [member("run/metrics.json", "$.splits.*.*_by_read_depth_quartile"), member("run/failures.json", "$.grouped.cnn_abs_error_over_2_*")]),
    ("FAMILY", "step_worst_to_best_allow_uatg: CNN 1.134 vs 0.405; 82% of CNN SSE from a 49-record family (MSE 3.98 vs 0.59); random split opposite (0.314 vs 0.723)",
     "sec:errors, tab:perlib", "companion_computed", [member("run/failures.json", "$.*.step_worst_allow_uatg"), member("run/metrics.json", "$.splits.*.per_library_mse"),
                                                                    article("section 'Errors concentrate...' (45 of the 49 family records contain an ATG: article text only)")]),
    ("VERIFY", "verify.py checks all passed; clean-environment rerun identical predictions (grouped CNN MSE 0.559972 both times)",
     "sec:provenance, tab:verify, tab:cleanroom", "companion_computed", [member("run/verify.json", "$.checks"), member("receipts/clean-room/compare-with-original.json", "whole file")]),
    ("PROTOCOL", "Protocol registered 08:56:32Z, amended 09:00:14Z before test scoring (example rule only), nine clarifications after scoring",
     "sec:methods", "registration record", [repo("companion/PROTOCOL.md", "header and clarifications"), member("receipts/protocol-registration.log", "whole file")]),
    ("ORTHRUS", "Orthrus excluded: mamba-ssm build failed without CUDA", "sec:models", "execution record",
     [member("receipts/orthrus-install-attempt/install-attempt-2.log", "whole file")]),
    ("TESTS", "pytest 10 passed, 1 skipped (no UTR_WORK); 11 passed with UTR_WORK; smoke 213 s", "app:repro", "execution record",
     [member("receipts/environment-and-tests-receipt.txt", "whole file")]),
    ("L-MRNABENCH", "mRNABench compositional-split drops (0.34, 0.33, 0.17) and saved results (0.862, 0.788, 0.649, 0.821; 0.729, 0.619)",
     "sec:background, sec:utrlm", "literature (not re-retrieved)", [article("sections 'Two splits...' and 'Frozen UTR-LM features...'")]),
    ("L-UTRLM", "UTR-LM ablation: frozen + MLP Spearman 0.6 vs 0.962 fine-tuned", "sec:background, sec:utrlm",
     "literature (not re-retrieved)", [article("section 'Frozen UTR-LM features...'")]),
    ("L-SAMPLE", "Sample et al.: MRL definition; variant r2 0.555 across 1,597 SNV pairs; low-read noise", "sec:background, sec:device",
     "literature (not re-retrieved)", [article("assay section; Variant effects paragraph")]),
    ("L-KAROLLUS", "MPRA-trained models correlate 0.11-0.25 with six endogenous datasets", "sec:limitations, fig:karollus",
     "literature (not re-retrieved)", [article("section 'What this evidence does not support'")]),
    ("L-CASTILLO", "MRL omits the ribosome-free fraction", "sec:background, sec:limitations", "literature (not re-retrieved)",
     [article("section 'What this evidence does not support'")]),
    ("FIGURES", "Companion figures (paired differences, accuracy vs cost, error by library and depth) and flowchart", "fig:paired, fig:cost, fig:errors, fig:flow",
     "companion_computed (figures)", [repo("article/assets/fig-paired-differences.png", "figure"), repo("article/assets/fig-accuracy-vs-cost.png", "figure"),
                                       repo("article/assets/fig-error-by-library-and-depth.png", "figure"), repo("article/assets/06-selection-flowchart.svg", "figure")]),
    ("I-MAIN", "Interpretation: CNN for MRL values on new families; no supported pick-list difference; frozen UTR-LM not justified on this evidence",
     "abstract, sec:discussion", "interpretation", [member("run/metrics.json", "$.splits.*.comparisons")]),
]


def main() -> None:
    ledger = {
        "schema_version": 1,
        "status": "historical_imported: every value comes from the 2026-09-30 companion run (results archive) or the cited "
                  "literature; nothing was recomputed or reproduced during migration",
        "claims": [{"id": i, "claim": c, "manuscript": loc, "evidence_class": cls, "evidence": ev} for i, c, loc, cls, ev in CLAIMS],
    }
    (ROOT / "evidence/paper-migration").mkdir(parents=True, exist_ok=True)
    (ROOT / "evidence/paper-migration/claims-ledger.json").write_text(json.dumps(ledger, indent=2) + "\n")
    print(f"claims ledger: {len(CLAIMS)} claims")


if __name__ == "__main__":
    main()
