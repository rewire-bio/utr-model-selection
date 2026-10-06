# Notice: third-party material used by this companion

This archive contains only original code and text written for this article: `utr_baselines.py`, `verify.py`, `make_figures.py`, `test_utr_baselines.py`, `PROTOCOL.md`, `README.md`, `NOTICE.md`, `pyproject.toml`, `uv.lock` and the tutorial notebook. The licence for these files is to be set at publication; none is asserted here.

Nothing below is redistributed. Each item is downloaded at runtime by `utr_baselines.py fetch` and checked against the SHA-256 recorded in `PINS`.

| Item | Source | Terms as recorded on 2026-09-30 |
|---|---|---|
| Processed designed-library records (`mrl-sample-designed.parquet`) | Hugging Face `morrislab/mrl-sample` @ `ef67f7cf8a999bb1c412ad6551aa7d9f901cbb95`, derived from Sample et al. (2019) | Dataset card licence field: `unknown`. Do not redistribute. |
| Designed-library metadata (`GSM3130443_designed_library.csv.gz`) | NCBI GEO sample GSM3130443 (series GSE114002) | GEO public record; original data from Sample et al. (2019). Not redistributed. |
| UTR-LM checkpoint `ESM2_1.4_five_species_TrainLossMin_6layers_16heads_128embedsize_4096batchToks.pkl` and UTR-LM's modified ESM package (`Scripts/esm/`) | GitHub `a96123155/UTR-LM` @ `b77b589bf182eb9de6a1a5024fa09d44294d94fc` | Repository licence GPL-3.0. The ESM files carry Meta's MIT header and were modified by the UTR-LM authors. Imported at runtime from the download directory; not copied into this archive. |

Scientific sources: Sample PJ et al. *Nat Biotechnol* 2019;37:803–809 (doi:10.1038/s41587-019-0164-5); Chu Y et al. *Nat Mach Intell* 2024;6:449–460 (doi:10.1038/s42256-024-00823-9); Shi R et al. mRNABench, bioRxiv 2025 (doi:10.1101/2025.07.05.662870).

The historical split and the composition replay reproduce the rewire-benchmarks local run at commit `ca73fa47136d182f2d4ddb083d084712198fc0e2` (MIT). No code was copied from it; the replay was reimplemented from its documented configuration and checked against its published split hash and MSE.
