# Protocol `utr-mrl-designed-choice-v1` (registered 2026-09-30, before any new method was scored on a test set)

Question: for the Sample et al. (2019) designed 5′UTR library, does a small supervised CNN or a frozen UTR-LM representation predict mean ribosome load (MRL) better than cheap baselines, by enough to matter?

## Data and population
- Processed records: Hugging Face `morrislab/mrl-sample`, file `mrl-sample-designed.parquet`, revision `ef67f7cf8a999bb1c412ad6551aa7d9f901cbb95`, SHA-256 `8b8c57581d472e89a21f8b468b3b0599f6c235c01423264561e6c302d78927d4`. Columns used: `sequence`, `target_mrl_designed`. 100,017 rows, no missing targets, no exclusions.
- Metadata: GEO `GSM3130443_designed_library.csv.gz` (SHA-256 `b72ac298cb0f4d21f911d330c0def06f8d94f15d9f8cc22f3a50ae87a7ef7ee5` at retrieval on 2026-09-30). Columns used: `utr`, `library`, `mother`, `total`, `rl`. Joined one-to-one on the 50-nt insert; `rl` must equal `target_mrl_designed` exactly for every row.
- Target: MRL, the read-weighted mean number of ribosomes per mRNA across polysome fractions (single measurement column `rl`; the designed library has one GEO sample, so no replicate averaging occurs).

## Input tracks (coordinates frozen)
- `full`: the 855-nt processed sequence. Positions 0–24 are the constant 25-nt defined leader; 25–74 the variable 50-nt insert; 75–854 a constant eGFP coding and downstream sequence. Used only by the historical replay configuration.
- `utr`: the 50-nt insert, `sequence[25:75]` (0-based, half-open). All learned and cheap methods below use this track because every other position is constant. Preparation asserts that the leader and the 780-nt tail are identical in all rows.
- `annotation`: features computed from the insert plus the known reporter context (the eGFP start codon begins immediately after position 74): uAUG count, out-of-frame and in-frame uAUG presence, uAUG followed by an in-frame stop within the insert, number of stop codons, and the Kozak −3 purine indicator plus one-hot of positions −3..−1 relative to the main AUG.

## Splits
- `historical`: the mRNABench/rewirebench seed-2541 random split (70,011 / 15,003 / 15,003), reconstructed from source row order and checked against split SHA-256 `00e287b18ba4e90cb682af6e3fcdfc97e07f2b4b25d13265cd0eca37996536a2`. Its test set was already used for two published controls, so every new result on it is **exploratory replay**. It is a random split, not homology-separated.
- `grouped`: new. Records are linked if they share a GEO `mother` sequence or share any identical 20-nt substring; connected components are groups. Components holding more than 1% of all records go to training. The remaining components are shuffled with seed 20260930 and assigned in that order to test until test reaches 15% of all records, then validation to 15%, then training. Registered before any method was scored on it. It is still **exploratory**: whole-dataset label summaries by sub-library were viewed before registration, and it is not an untouched cohort.

## Methods (fit on training only; hyperparameters selected on validation only; test used once per method)
| ID | Track | Features / model | Adaptation |
|---|---|---|---|
| `train_mean` | none | constant training mean | none |
| `comp_full_replay` | full | log1p length, A/C/G/T fractions, unknown fraction; sklearn `RidgeCV(alphas=[1e-3,1e-2,0.1,1,10])`, GCV on training only, no scaling | historical configuration, replayed exactly |
| `comp_utr` | utr | A/C/G/T fractions and GC fraction | ridge |
| `kmer_utr` | utr | counts of all 1-, 2- and 3-mers (84) | ridge |
| `onehot_pos` | utr | position-specific one-hot (200) | ridge |
| `annot` | annotation | uAUG/uORF/stop/Kozak features | ridge |
| `cheap_combined` | utr + annotation | `kmer_utr` + `onehot_pos` + `annot` concatenated | ridge |
| `cnn` | utr | one-hot CNN: 3×Conv1d(120 filters, width 8, same padding, ReLU), dense 40, dropout 0.2, linear output (Optimus 5-Prime-style) | trained from scratch |
| `utrlm_mean_ridge` | utr | UTR-LM `ESM2_1.4_five_species` frozen, final-layer embeddings averaged over the 50 insert tokens (128-d) | frozen + ridge |
| `utrlm_pos_ridge` | utr | same frozen final-layer embeddings, all 50 positions flattened (6,400-d) | frozen + ridge |
| `utrlm_cnn` | utr | same frozen per-position embeddings (128 channels) fed to the `cnn` architecture | frozen + trained CNN head |

- Ridge (all except the replay): features standardised with training mean/SD; target centred on the training mean; alpha chosen from {1e-3, 1e-2, 0.1, 1, 10, 100, 1e3, 1e4} by validation MSE; final model is the training-only fit at that alpha.
- CNN heads: target standardised with training mean/SD; MSE loss; Adam, learning rate 1e-3; batch 128; at most 20 epochs; stop after 3 epochs without validation-MSE improvement and restore the best epoch. Seeds 0, 1, 2. Training may use Apple MPS after a CPU/MPS equality check on the initial model; test predictions are computed on CPU.
- UTR-LM: official checkpoint `Model/Pretrained/ESM2_1.4_five_species_TrainLossMin_6layers_16heads_128embedsize_4096batchToks.pkl` from `a96123155/UTR-LM` at commit `b77b589bf182eb9de6a1a5024fa09d44294d94fc` (SHA-256 `2fc9b7b09a1167aa7fd4694df6a4a105d1939ae7099168bed3b061beb55917c0`), 6 layers, 128-d, 16 heads, alphabet `AGCT`, input `<cls>` + insert + `<eos>`. Loaded with `strict=True`. Embeddings are computed on CPU only, because on the test machine MPS output diverged from CPU output (masked-nucleotide accuracy fell from 0.41 to 0.34). The run fails unless CPU masked-nucleotide accuracy on 1,000 training inserts exceeds the majority-base rate.
- Eligibility of the checkpoint: the paper describes the baseline model as pretrained on unlabelled Ensembl 5′UTRs from five species with masked-nucleotide prediction only. It was not trained on MRL labels or on Sample library sequences. The human-UTR fragments in this library come from human 5′UTRs, which are likely present, unlabelled, in that corpus. The UTR-LM MRL checkpoints and the multimolecule `utrlm-mrl` checkpoint were trained with Sample et al. MRL data and are excluded.

## Metrics
- MSE and MAE in MRL units; R² = 1 − SSE/SST with SST about the test mean; Pearson and Spearman correlation, reported as unavailable (null) for constant predictions; coverage (scored/test records).
- Prioritisation endpoint: a record is "high-MRL" if its measured MRL is at or above the 90th percentile of that split's training labels. Capacity k = floor(1% of test records). Precision@k = fraction of the k highest-predicted test records that are high-MRL (ties broken by lower source index). Enrichment = precision@k / test base rate.

## Uncertainty and decision rule
- Dependence unit: the connected component defined above, for both splits. Training-label intraclass correlation within components is reported to show whether the dependence is real.
- Sampling uncertainty: 2,000 cluster-bootstrap resamples of test components (seed 7), percentile 95% intervals for metrics and for paired differences against the reference.
- Training-seed variability: per-seed test metrics for CNN heads, reported separately. Paired intervals use seed 0, fixed in advance.
- Reference cheap baseline: the ridge method (`comp_utr`, `kmer_utr`, `onehot_pos`, `annot`, `cheap_combined`) with the lowest validation MSE on that split.
- A method is declared to add practical value over the reference if its MSE is lower by at least 0.10 MRL² and the 95% interval for that difference excludes zero. For prioritisation, the precision@k gain must be at least 0.05 with an interval excluding zero. Otherwise the result is "no supported difference", or "difference below the practical threshold".
- The same rule compares `utrlm_*` against `cnn` (frozen representation versus supervised task model) and `utrlm_cnn` against `cnn` (does the frozen input help the same head?).
- All results are exploratory. None is a confirmatory claim, because no untouched cohort exists for this library.

## Resources
Wall time per stage, peak resident memory per method process, feature-cache bytes, download bytes, device and hardware. Timing excludes environment installation.

## Examples (deterministic)
On the grouped test set: the records whose measured MRL is closest to the 10th, 50th and 90th percentiles of test labels (ties to lower source index); the record with the largest absolute seed-0 `cnn` error; and the lowest-index `snv` variant record (its `mother` differs from its own insert) whose `mother` is also in the test set, shown with that reference sequence.

---

## Reporting clarifications (added 2026-09-30, after scoring)

Everything above this line is the registered protocol, unchanged: registered 08:56:32Z (SHA-256 `d5b4211e…`) and amended once before any test scoring at 09:00:14Z (example rule only; SHA-256 of that version `f070bdca…`). To check it, hash the first 8,604 bytes of this file (for example `head -c 8604 PROTOCOL.md | shasum -a 256`). The clarifications below correct or explain wording. None changes a fitted method, split, prediction, threshold or verdict.

1. **Units.** MSE is in squared MRL units (MRL²); MAE is in MRL units. The Metrics line above says "MSE and MAE in MRL units", which is wrong for MSE. The practical threshold of 0.10 is in MRL², as registered.
2. **Checkpoint provenance.** The sentence "It was not trained on MRL labels or on Sample library sequences" is stronger than the evidence supports. What the documents support: the UTR-LM paper describes a baseline pretrained on unlabelled five-species Ensembl 5′UTRs with masked-nucleotide prediction only; `ESM2_1.4_five_species…pkl` is the only pretrained file whose name carries no Cao, downstream-library, secondary-structure or free-energy token, and it loads strictly into the plain ESM2 class with no supervised heads. No retrieved text names this file explicitly, and no sequence-overlap audit was run. Natural human 5′UTR fragments in this library may appear, unlabelled, in the Ensembl corpus.
3. **Why the other checkpoints were excluded.** The UTR-LM `FS4.x` checkpoints, and multimolecule `utrlm-mrl` (converted from `ESM2SISS_FS4.1`), included Sample et al. random-library sequences in pretraining, together with structure and free-energy tasks. The retrieved sources do not establish that these pretrained checkpoints saw MRL labels. They are excluded for downstream-library sequence exposure, not for proven label leakage. Explicitly MRL-fine-tuned task checkpoints are a separate category and were not used.
4. **Grouped split population.** Forcing the single component larger than 1% of records into training removes 14,101 records (14.1%) from possible evaluation. That component is 98% genetic-algorithm designs (`target_*` and `step_*`; mean MRL 6.59 against 5.74 overall). The grouped test set therefore contains no `step_random_to_best_no_uatgs` records and few other genetic-algorithm designs, and its high-MRL share is 0.055 against 0.095 in the historical test set. The grouped track is a defined transfer test to sequences with no shared 20-nt substring or GEO mother in training. It is not a leakage-free estimate for every designed sequence. Counts by library and split: `failures.json` (`describe_failures.py`).
5. **Bootstrap capacity.** In each bootstrap draw, capacity is the registered review fraction, floor(1% of the resampled record count), not a literal fixed 150. Resampled test sizes ranged from 12,420 to 31,800 records (historical; large components can repeat) and from 14,032 to 16,081 (grouped), giving capacities of 124–318 and 140–160 (means 150.7 and 149.5). An independent reconstruction of the 2,000 draws reproduced these depths (`parent-utr-bootstrap-depths.json`). Every draw had a capacity of at least 124, so no top-k list was empty. Point estimates use k = 150 on the observed test sets.
6. **Ties and chance.** Precision@k breaks ties by lower source index. For the constant `train_mean` predictor every record ties, so its observed precision (0.053 historical, 0.040 grouped) is an artefact of that rule. The chance expectation is the test high-MRL share (0.095 historical, 0.055 grouped). Tie order is a deterministic convention, separate from sampling uncertainty.
7. **Resource scope.** Each method runs in its own process, so peak RSS is per method and per split. CNN `fit_seconds` covers all three seeds; the seed-0 time is in `fit.json` under `seeds`. Ridge times include the validation alpha search. Every timed CNN interval ends with a transfer of predictions to CPU, which synchronises MPS. All times come from one shared laptop that was swapping (about 7 GB) and running other work during the grouped fits. They are receipts, not a controlled speed benchmark.
8. **Device checks.** The registered CPU/MPS check compared outputs of each untrained CNN. After training, validation MSE computed on the training device and on CPU agreed within 3.3e-8 for all twelve CNN fits (`failures.json`, `cnn_device_parity`). This is agreement of one metric, not a general device-parity guarantee. The UTR-LM CPU/MPS discrepancy stands; embeddings are CPU only.
9. **Thresholds.** The 0.10 MRL² and 0.05 precision thresholds are this comparison's prespecified decision criteria. They are not validated measures of biological utility. "No supported difference" does not establish equivalence.
