# Model selection for 5′UTR translation experiments

Status: HISTORICAL STUDY IMPORTED; NEW HARNESS EXECUTION UNAPPROVED

The scientific protocol is [`companion/PROTOCOL.md`](companion/PROTOCOL.md),
`utr-mrl-designed-choice-v1`, registered on 30 September 2026. Its original
registered text and post-scoring clarifications remain preserved. It describes
the Sample designed-library population, source hashes, historical and grouped
splits, eleven methods, validation-only model selection, cluster bootstrap,
practical thresholds and exploratory scope.

The imported predictions, receipts and measurements are in
[`downloads/utr-baselines-results.zip`](downloads/utr-baselines-results.zip).
The manuscript formats those archived measurements. Rebuilding it or running
unit tests does not establish an independent reproduction.

The root `study.json` and `configs/` are migration scaffolding. The root experiment
entry point deliberately fails; they are not an executable scientific protocol.
A future harness run requires an explicit protocol amendment with concrete
inputs, outputs, compute/storage budget and tolerances, then owner approval.
The companion README documents the historical runnable workflow and observed
runtime, including the longer expected CPU-only runtime.

The October 2026 maintenance audit strengthens artifact validation and test
coverage without changing the registered estimands, methods, splits or archived
results. See [`evidence/repository-audit.md`](evidence/repository-audit.md).
