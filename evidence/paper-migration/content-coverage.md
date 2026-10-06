# Content coverage: original article to manuscript

Original: `article/published-original.md` (byte-identical published copy; SHA-256
`3705cd10d8f8fb42ef305863d385b196f8095a01ba739a48329f5d1e3ba8572f`), *Choosing a Model for 5′UTR Translation
Experiments: Cheap Features, a Small CNN or Frozen UTR-LM* (30 September 2026). Manuscript: `paper/main.tex` →
`paper/build/main.pdf`. The original is retained unchanged as Supplement S1 (repository file and PDF attachment
`S1-published-original.md`).

Generated tables come from `downloads/utr-baselines-results.zip` members read in memory by
`scripts/paper_extract.py`; every cell of manuscript Tables 1 and 2 (original Tables 2 and 3, including verdicts) and
the read-depth, family, dependence, base-rate and resource numbers are cross-checked against the values printed in the
original; recorded result 0 mismatches (`paper/generated/extraction-receipt.json`).

Numbering map — original → manuscript: Table 1 (decision summary) → Table 4; Table 2 → Table 1; Table 3 → Table 2;
Table 4 → Table 3. Figure 1 → 1; Figure 2 → 2; Figure 3 → 3; Figure 4 → 4; Figure 5 → 5; Figure 6 (flowchart) → 7
(Appendix D); Figure 7 (Karollus) → 6.

| Original section / element | Scientific content | Manuscript location | Notes |
|---|---|---|---|
| Front matter: description, excerpt | Grouped MSE reduction +0.216 [+0.176, +0.252]; P@150 +0.020 [−0.088, +0.132] not supported; UTR-LM no supported gain; one assay, ~70,000 labels, exploratory | Title, status box, Abstract | |
| FAQ 1 (CNN better than cheap features?) | 0.776 → 0.560; precision not supported; interval too wide for equivalence | Abstract; §4.1; Table 2 | |
| FAQ 2 (frozen UTR-LM help?) | Ridge head worse; CNN head −0.010 [−0.034, +0.016]; random +0.021 [+0.009, +0.034] and P@150 −0.127; one frozen checkpoint | Abstract; §4.2; Table 2 | |
| FAQ 3 (why splits differ) | 79.3% overlap; 14,101-record family forced into training; base rates 0.055 vs 0.095; not attributable to leakage alone | §3.2; §4.6 (Split design) | |
| FAQ 4 (UTR-LM on MPS) | MPS differs from CPU; MLM 0.412 → 0.335; CPU used | §4.6 (Device divergence); §3.3 | |
| FAQ 5 (protein output / endogenous) | IVT eGFP reporter, 50-nt insert, HEK293T; MPRA models weakly correlated with endogenous | Abstract; §6 Limitations; Figure 6 | |
| Lead paragraphs | Options; 100,017 UTRs; Sample et al.; mRNABench processing; grouped split result; P@150 definition, 86 vs 83; exploratory scope; ~57 min rerun | Abstract; §1; §3.1; §4.1; App. A | |
| Table 1 (decision summary, 7 rows) | All rows | Table 4 | Wording "you" → neutral |
| §"The assay measures ribosome loading…" + Figure 1 | MRL definition; construct; GEO; library composition (35,212; 3,577; 80 trajectories / 7,526); mcherry label; two undocumented labels; single measurement; chemistry not stated; 805 of 855 nt constant; full-sequence replay ≈ insert-only (<0.001; 1.914) | §2.1; Figure 1; §3.1 | |
| §"Three kinds of model…" | Cheap ridge features (84; 200; annotation; combined); reference rule; CNN design and seeds; UTR-LM checkpoint (6 layers, 128 dims, 1.21 M); three heads; workflows not matched architectures; frozen vs fine-tuned; documentary case for checkpoint; excluded FS4.x and utrlm-mrl; MLM 0.416 vs 0.329; validation-only selection; test once | §3.3 | Ridge alpha grid and CNN training settings added from `companion/PROTOCOL.md` |
| §"Two splits answer different questions" | Random split (seed 2541; 70,011/15,003/15,003; prior use; relatives; 33,575 families; 79.3%; ICC 0.495); grouped split (69,996/15,017/15,004; registered; label summaries viewed; 14,101 family 14.1%, 98% GA, 6.59 vs 5.74; composition and base-rate differences); compare within split | §3.2; App. Table 10 | |
| mRNABench paragraph + Figure 2 | Kozak/uAUG hold-out drops (0.34, 0.33, 0.17); utrlm point matches utrlm-te-el; utrlm-mrl exclusion | §2.2; Figure 2 | |
| §"Metrics and the decision rule…" | MSE; training-mean 2.224; R² definition (not r²); P@150 definition, 7.402 cut-off, ties by source index, chance 0.055/0.095; cluster bootstrap 2,000 (Field & Welsh), capacity 140–160 / 124–318; seed variability separate; no assay variability; decision rule and thresholds; not equivalence | §3.4; §3.5 | Verdict categories spelled out as implemented in `utr_baselines.py` `_verdict` |
| §"The CNN reduced error…" + Table 2 | All 10 methods × both splits, times, memory; Input and Adaptation columns | Table 1 | Input and Adaptation columns condensed into a key in the Table 1 caption (layout) |
| Table 3 + Figure 3 | 10 paired comparisons and verdicts; MSE forest plot | Table 2; Figure 3; App. Table 5 (all 22 registered comparisons from archive) | |
| Paragraphs after Table 3 | CNN interval above 0.10; seeds 0.559–0.570; 86 vs 83, ~10× chance; ±0.1 not excluded; seeds 0.533–0.580; random 118 vs 87 | §4.1; App. Table 7 | |
| §"Frozen UTR-LM features…" | Ridge worse; CNN head 0.570 vs 0.560; random +0.021 / −0.127; validation vs test ordering; UTR-LM fine-tuning ablation (0.6 vs 0.962); mRNABench saved results (0.862, 0.788, 0.649, 0.821; 0.729, 0.619); not a replication | §4.2; §2.2 | |
| §"Accuracy cost…" + Figure 4 | 3,417 s (56.9 min); hardware; shared and swapping; ridge 15–21 s, <0.6 GB; CNN 174–313 s per seed; 205/250 s; 1.2–1.3 GB; 588/733 and 876/777 s; CPU epoch 151 vs 11 s; 4.87 MB checkpoint; 134.8 s embedding (1.76 GB); 1.28 GB cache; 3.2 GB per-position ridge | §4.3; Figure 4; App. Table 12 (per-step times from `run-log.json`) | |
| §"Six declared examples…" + Table 4 | Example rule; reporter context; six records and predictions; ATG/Kozak observations; largest error (1.99 vs 6.70–8.10; 328 reads vs 616); SNV pair (+0.66; predictions +0.17/+0.07/−0.06/+0.32) | §4.4; Table 3 | Insert printed beneath each row |
| §"Errors concentrate…" + Figure 5 | Read-depth quartiles (0.785/0.419; 1.024/0.606); 289 errors >2 MRL, median 485 vs 616 reads; Sample et al. noise note; trajectory family (1.134 vs 0.405; 210 records, 5 families; 49-record family 82% of SSE, 3.98 vs 0.59; random split opposite 0.314 vs 0.723) | §4.5; Figure 5; App. Tables 8 and 9 | |
| §"Variant effects, split design and device choice" | Sample r² 0.555 over 1,597 pairs; split-design drop +0.422 → +0.216; MPS divergence 7.6; MLM 0.412 → 0.335; CNN parity 1.1e-7 untrained and ~3e-8 trained (12 fits); test predictions on CPU | §4.6; App. Table 11 | |
| §"The choice depends…" + Figure 6 | Recommendations by use; no supported difference is a finding, not equivalence | §5.1; Figure 7 (App. D) | |
| §"What this evidence does not support" + Figure 7 | Protein output; endogenous (0.11–0.25); other reporters; few labels; variable length; other foundation models / Orthrus exclusion; confirmatory claims | §6 Limitations; Figure 6; §3.3 (Orthrus) | Added: uncertainty scope, checkpoint provenance, platform, review |
| §"Reproduce the comparison" | Commands; test counts; smoke timings 213/199/405/190 s; tutorial 230 s; run-all steps; 15 downloads; split hash; grouped_split code; GIANT_FRACTION 0.01, seed 20260930; verify.py checks (max diff 0; 1.4e-7; 1.914439715839851); clean rerun (18 deterministic fits + grouped seed-0 CNN; 0.559972); no cross-platform tolerance; archive contents; PROTOCOL registration, amendment and nine clarifications | App. A; App. B (verbatim from `companion/utr_baselines.py` lines 221–239); §3.6; §3 opening; §7; App. Tables 13–14 | Commands adapted (comments moved to prose); not re-executed |
| §"What would change this recommendation" | Fresh cohort; replicate; CNN P@150 gain; learning curve; fine-tuned or other pretrained model beating CNN by >0.10 | §5.2 | |
| Disclosure | Automated drafts, reviews and fact checks (Claude Opus); Codex mechanical checks; no human review | §8 | Extended with this manuscript's drafting and review |
| Sources and artifacts (12 bullets) | Bibliography | `paper/references.bib` (17 entries; supplement, repository and documentation links split into separate entries) | DOIs only where given by the original (Field & Welsh) or the original companion NOTICE (Sample, Chu, mRNABench) |

## Additions beyond the original article (archived evidence only; no new computation)

- App. Table 5: all 22 registered comparisons (the original printed 10).
- App. Tables 6–14: secondary metrics (MAE, Pearson, Spearman, enrichment, validation MSE, coverage), per-seed results,
  read-depth quartiles for both splits, per-sub-library MSE, library composition by split, CNN device parity, per-step
  wall times, `verify.py` checks and the clean-environment comparison.

## New statements in the manuscript (not in the original article)

- Introduction contributions list and framing of the three options (rephrased after review to avoid a prevalence claim).
- §3.5: the statement that none of the 22 registered comparisons is multiplicity-adjusted; the note that "worse than
  reference" comes from the companion's verdict function, not the registered protocol.
- §4.1: the sentence on single cheap feature sets versus cheap combined (from App. Table 5).
- §4.2: UTR-LM ridge heads also worse than the one-hot CNN (from App. Table 5).
- §8: the manuscript's own drafting and AI-review disclosure. (A sentence attributing the protocol and code to AI agents
  was removed after review because no artifact supports it.)

## Not carried into the manuscript body (retained in Supplement S1)

- Reader-facing second-person phrasing (the advice "Check error by family" and "compare CPU and accelerator outputs on
  your own setup" are restored in neutral form in §4.5 and §4.6), FAQ format and front-matter fields (SEO title, tags).
- Site-relative download links (`/downloads/...`); the manuscript names repository paths instead.
