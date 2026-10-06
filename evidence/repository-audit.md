# Repository audit, 6 October 2026

Scope: methods, split construction, train/validation/test boundaries, uncertainty,
model-selection rules, prediction alignment, CLI stages, artifact provenance,
independent checks, CI, archived numerical evidence and the paper build.
The review used main revision `1222a0d`. It does not establish a fresh independent
scientific reproduction or cross-platform training equivalence.

## Findings and resolution

- [#2](https://github.com/rewire-bio/utr-model-selection/issues/2): evaluation
  silently accepted incomplete methods/splits and nonfinite predictions.
  It now requires the complete registered comparison, exact validation/test row
  coverage and split labels, finite main/seed predictions and validation scores.
- [#3](https://github.com/rewire-bio/utr-model-selection/issues/3): verification
  could ignore NaN discrepancies or treat truncated data as smoke. It now requires
  explicit run mode, exact population/order and source labels/inserts, pinned
  source hashes, complete method/split coverage, finite predictions/discrepancies
  and the deterministic full grouped allocation.
- [#4](https://github.com/rewire-bio/utr-model-selection/issues/4): positional
  embedding caches and predictions were not bound to prepared records. New receipts
  store record, embedding and prediction digests. Stale artifacts fail; stage
  outputs cannot be overwritten. The explicit historical compatibility option
  permits missing old hashes only, never mismatched recorded hashes.
- [#5](https://github.com/rewire-bio/utr-model-selection/issues/5): root test/CI
  did not exercise companion tests. `make test` now runs the maintained suite and
  immutable archive checks; push/PR CI additionally checks paper table extraction.
  The unrelated pi-fixture root protocol was replaced with accurate migration
  status and a pointer to the preserved scientific protocol.

A second review found that the paper's fixed source-line inclusion would become
incorrect after code edits. Its grouped-split listing now comes from the immutable
historical code archive, with a recorded digest. The paper explicitly separates
maintenance safeguards from historical scientific measurements.

## Validation and impact

- 27 synthetic regression tests passed; one full-training-dependent test was
  intentionally skipped. Tests include malformed prediction populations, NaN/Inf,
  changed/reordered caches, preserved existing outputs, legacy hash mismatch,
  explicit source population and an independently expanded cluster-bootstrap
  precision calculation.
- The read-only `scripts/check_saved_predictions.py` checked all 22 archived
  method/split prediction files against the pinned source labels and original
  prepared population. Independent BFS component IDs and the seeded grouped allocation
  also matched the original records exactly. Every validation/test prediction and saved seed was finite
  and complete. Main regression metrics matched archived values exactly (maximum
  absolute difference **0**). This did not train or bootstrap any model.
  Hashes and per-method counts are in `audit-saved-predictions.json`.
- Historical downloads, published original text and figures passed digest checks.
  The link-adjusted article copy remains unchanged. The manuscript extractor
  reported zero numeric mismatches; the rebuilt PDF has 25 pages and zero
  LaTeX/BibTeX warnings. Changed appendix pages were visually inspected.

No evidence found in this review requires a numerical correction or invalidates
the published conclusions. The known limitations remain material: exploratory
reuse of the historical test set, label summaries seen before grouped registration,
the large component excluded from grouped evaluation, one assay/library/context,
uncertain checkpoint sequence overlap and no established cross-platform training
reproduction. Missing retrospective embedding hashes cannot be manufactured;
new safeguards protect future runs, while archived reproduction receipts retain
their original evidential scope.

Issue #1 concerns a separate accessible blog rewrite. It is not a scientific
correctness defect and is not closed by this code audit.
