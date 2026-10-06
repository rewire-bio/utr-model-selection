# Independent review: historical-evidence manuscript migration (utr-model-selection)

**Reviewer:** Claude Opus (`claude-opus-5-5`), an independent AI instance. I did not write the manuscript. This is an automated review, not a human scientific review.
**Date:** 2026-10-06
**Object reviewed:** `paper/main.tex`, `paper/references.bib`, `paper/generated/*.tex`, `paper/build/main.pdf` (SHA-256 `bfdf01e9…0429`, 24 pages; matches `build-receipt.json`)

## Scope and what I did

- **Read in full:** `article/published-original.md`; `paper/main.tex`; `paper/references.bib`; all 14 `paper/generated/*.tex` and `extraction-receipt.json`; `evidence/paper-migration/{content-coverage.md,status.json,build-receipt.json}`; the `claims-ledger.json` entries (all 27 summaries, plus COST, EXAMPLE-NOTES and FAMILY in full); `companion/{PROTOCOL.md,README.md,NOTICE.md}`; `companion/utr_baselines.py` lines 215–242 and `_verdict`; `protocol.md` (head); `Makefile`; `paper/build/{warnings.txt,bibtex.stdout.txt,main.blg,main.toc}`; and a grep of `main.log` for warnings, overfull boxes and undefined references (none found).
- **Archive lookups (read-only, formatting only, no recomputation of statistics).** I read these members from `downloads/utr-baselines-results.zip`: `run/metrics.json`, `run/failures.json`, `run/prepare.json`, `run/verify.json`, `run/embed.json`, `run/run-log.json`, `run/run-all.log` (tail), `receipts/clean-room/compare-with-original.json`, `receipts/protocol-registration.log`, `receipts/mps-vs-cpu-utrlm-receipt.txt`, `receipts/environment-and-tests-receipt.txt` and `MANIFEST.md`. I compared every cell of Tables 1, 2, 3, 5, 6, 7, 8, 9, 10, 11, 12, 13 and 14 and every macro against these members, after rounding to the printed precision. I also compared the main-text numbers with the original article.
- **Integrity checks:**
  - `article/published-original.md` SHA-256 is `3705cd10…`, which matches the coverage file and the migration audit.
  - The PDF attachment `S1-published-original.md` (extracted with `pdfdetach`) has the same hash.
  - `companion/{utr_baselines.py,PROTOCOL.md,NOTICE.md,README.md}` are byte-identical to the copies in `downloads/utr-baselines.zip`.
  - The three companion figure PNGs in `article/assets/` are byte-identical to the copies in the results archive.
  - The DOIs for Sample, Chu and mRNABench match `companion/NOTICE.md` exactly.
- **Rendering:** `pdftoppm -r 50` of all 24 pages. **I viewed pages 1–24 at 50 dpi.** I also viewed these at higher resolution:
  - page 8 at 110 dpi (Tables 1 and 2);
  - the top of page 10 at 120 dpi (Figure 4 and Table 3);
  - the flowchart on page 23 at 100 dpi;
  - Figure 2 on page 4 at 100 dpi.

  Rendering worked. All temporary PNGs under `/tmp/utr-review/` have been deleted.
- **Not done:** I ran no experiments, `make`, `uv`, companion scripts, network fetches or statistical recomputation. I did not re-retrieve any literature, so I checked literature claims against the original article only, not against the primary sources.

## Overall assessment

The migration is faithful and careful.

- **Numbers:** Every numerical value I checked matches the archived results and the original article. This covers all 10 methods × 2 splits, all 22 comparisons and verdicts, the examples, seeds, secondary metrics, per-library values, read depth, parity, run log, `verify.py` checks, the clean-room comparison and every macro. I found no sign, rounding or verdict errors.
- **Status and framing:** The status box, running header, PDF metadata and the Reproduction-status box all state clearly that these are historical results and that independent reproduction is pending. "No supported difference" is never presented as equivalence.
- **Build and bibliography:** The build is clean (0 LaTeX and 0 BibTeX warnings, no undefined references). The bibliography is limited to the original's sources, and no DOIs are guessed.
- **Issues found:**
  - one loss of table content: the Input and Adaptation columns of original Table 2;
  - one mislabelled appendix table column: the Table 10 "Families" column;
  - one disclosure sentence that goes beyond the evidence;
  - several minor framing, consistency, layout and coverage-document inaccuracies.

**No blocking findings.** The manuscript is suitable once the three major findings are addressed.

## Findings

### Major

**1. Major: original Table 2 lost its "Input" and "Adaptation" columns, and the coverage map does not say so.**
- **Location:** `paper/main.tex` L309–330 (Table 1, PDF p. 8); `content-coverage.md`, row "§The CNN reduced error… + Table 2" ("All 10 methods × both splits, times, memory").
- **Evidence:**
  - Original Table 2 (`published-original.md` L95–106) has `Input` (none / insert / insert + reporter context) and `Adaptation` (none / ridge / trained from scratch / frozen + ridge / frozen + trained CNN) for every method.
  - Manuscript Table 1 keeps only the method names and metrics.
  - The information is only partly recoverable from §3.3. For example, the fact that `cheap_combined` and the uAUG/Kozak features use "insert + reporter context" while every other method uses the insert only is not visible in the table.
- **Fix:**
  - Restore the two columns. A narrow "Input / adaptation" column, or a stacked cell under the method name, would fit the current layout. Alternatively, add a compact key in the caption that maps each method to its input and adaptation.
  - Record the change in `content-coverage.md`.

**2. Major: the "Families" columns of Table 10 are mislabelled; the values are test-set families per sub-library.**
- **Location:** `paper/main.tex` L744–760 (Table 10 caption: "number of families (components) under each split"), PDF p. 20; `paper/generated/tab_composition.tex`.
- **Evidence:**
  - The values come from `failures.json` `{historical,grouped}.components_per_library`. These are test components: for example, `step_worst_to_best_allow_uatg` random = 38 and grouped = 5, which match "744 test records in 38 families" and "210 grouped-test records in 5 families" in §4.5.
  - Grouped `step_random_to_best_no_uatgs` shows 0 families although it has 2,499 records (2,479 train, 20 val). Under the printed label this is impossible.
  - The per-library values also do not sum to the split totals (random sum 9,816 against 9,640 test components) because families span sub-libraries. Nothing tells the reader this.
- **Fix:** Rename the columns "Test families" and change the caption to: "…and the number of test-set families (components with at least one test record in that sub-library); families can span sub-libraries, so columns do not sum to the 9,640 / 6,002 test components."

**3. Major: the AI disclosure adds a claim that neither the original nor the archive supports.**
- **Location:** `paper/main.tex` L599–600 (§8, PDF p. 14): "The original study, including the registered protocol and the companion code, was carried out with AI coding agents".
- **Evidence:**
  - The original disclosure (L273) says only that the article drafts, editorial reviews and fact checks were automated (Claude Opus), that the mechanical checks were run by Codex, and that the code was run on the described machine.
  - `MANIFEST.md` and `companion/README.md` mention a "parent Codex orchestration session" for the checks only.
  - No artefact I read states who wrote the protocol or the code. `content-coverage.md` lists only the manuscript's drafting and review as additions to the disclosure.
- **Fix:** Either remove the sentence and keep the original disclosure plus the manuscript-drafting statement, or keep it only after the study owner confirms it, and record that confirmation as its source in the ledger.

### Minor

**4. Minor: Table 3 caption contradicts §7 about embedded source sequence.**
- **Location:** `main.tex` L425–426 (PDF p. 10), which says "These six inserts are the only source sequences embedded in the results archive", against L590–591 (§7), which also names the constant 780-nt eGFP tail.
- **Evidence:** `MANIFEST.md` lists two embedded excerpts: the six inserts in `metrics.json` and the 780-nt tail in `prepare.json`.
- **Fix:** Change the caption to "These six inserts are the only variable-region source sequences embedded in the results archive (which also holds the constant 780-nt tail; Section 7)."

**5. Minor: the availability statement does not cover the manuscript's own copy of the licence-"unknown" excerpts.**
- **Location:** §7, `main.tex` L589–594.
- **Evidence:**
  - Table 3 and the embedded Supplement S1 reproduce six records from the processed dataset (insert, measured MRL, read count). The dataset card licence is "unknown" and NOTICE.md says "Do not redistribute".
  - §7 describes the redistribution question for the archive only.
  - Keeping these records is correct under the preservation policy, because the published article printed them.
- **Fix:** Add one sentence: "Table 3 and Supplement S1 reproduce these six records exactly as the published article did; they are subject to the same open owner decision."

**6. Minor: some literature-level generalisations are new or stronger than the original.**
- **Location and evidence:**
  - Introduction L113–117: "Three families of model are in common use" and "is attractive only if it improves accuracy". Neither appears in the original. The first is a field-level claim, cited to three papers that do not establish prevalence.
  - §4.2 L383: "which the UTR-LM authors' ablation favours strongly". The original gave the specific result with its conditions (random 50-nt library, rank split, MLP head, Spearman 0.6 vs 0.962). The manuscript moves those conditions to §2.2 and leaves an unconditioned generalisation here.
- **Fix:**
  - Introduction: "We consider three options: …". Delete "and is attractive only if it improves accuracy", or rephrase it as the study question.
  - §4.2: "This says nothing about fine-tuning; in the authors' own ablation, under a different library and split, fine-tuning outperformed a frozen model with an MLP head (Section 2.2)."

**7. Minor: the Reproduction-status box implies the clean rerun produced all values.**
- **Location:** `main.tex` L494–495 (PDF p. 12): "The values above are imported from the 30 September 2026 companion run and its same-machine clean-environment rerun."
- **Evidence:** The clean rerun repeated only the 18 deterministic fits and the grouped seed-0 CNN (Table 14). It did not repeat the other CNN fits, the bootstrap or `evaluate`.
- **Fix:** "The values above are imported from the 30 September 2026 companion run; a same-machine clean-environment rerun repeated a subset (Table 14)."

**8. Minor: Table 12 caption misdescribes how its fit rows relate to Table 1.**
- **Location:** `main.tex` L781–784 (PDF p. 21): "…so they differ slightly from the in-process fit times in Table 1".
- **Evidence:** For the CNN heads, Table 1 shows seed-0 times (205, 250, 269, 263 s), while Table 12 shows all three seeds plus start-up (588.5, 734.6, 877.4, 778.4 s). The difference is not slight. The in-process three-seed times (587.5, 733.0, 876.2, 776.7 s) appear only in §4.3.
- **Fix:** "…ridge rows differ slightly from the in-process fit times in Table 1; CNN rows cover three seeds, whereas Table 1 gives seed 0 (in-process three-seed totals are in Section 4.3)."

**9. Minor: the "worse than reference" category is attributed to the protocol.**
- **Location:** §3.5, `main.tex` L277–281: "The protocol declares… an interval wholly below zero is *worse than reference*."
- **Evidence:** PROTOCOL.md (L48) defines only "adds practical value", "no supported difference" and "difference below the practical threshold". "Worse than reference" comes from `_verdict` in `utr_baselines.py` (L840–847). The coverage file says this, but the manuscript text does not.
- **Fix:** "…; the companion's verdict function additionally labels an interval wholly below zero *worse than reference*."

**10. Minor: split naming is inconsistent across tables and figures.**
- **Location:** Table 6 (L689; PDF p. 19) and Table 13 (PDF p. 21) use "historical". Figures 3 and 4 read "Historical random split (replay)". Elsewhere the manuscript uses "random".
- **Fix:** Map "historical" to "random" in `paper_extract.py` for Tables 6 and 13. Add "('historical' in the figure panels and code is the random split)" to the captions of Figures 3–5.

**11. Minor: float placement and layout.**
- **Location and evidence:**
  - PDF pp. 3–5: §3 opens at the foot of p. 3 and its first sentence breaks mid-parenthesis ("(example rule" … "only)"). The sentence resumes on p. 5, after Figures 1–2 fill p. 4.
  - PDF p. 13: Table 4 (decision summary, cited in §5.1) floats into the middle of the §6 Limitations list.
  - PDF p. 17: almost empty. The Appendix C heading and one sentence are stranded because `[H]` Table 5 does not fit.
  - PDF p. 2: mostly blank after the table of contents (cosmetic).
- **Fix:**
  - Use `[tp]` for Figures 1–2, or move them after the first §3 paragraph.
  - Place Table 4 with `[t]` immediately after the §5.1 paragraph, or put a `\FloatBarrier` (package `placeins`) before §6.
  - Add `\clearpage` before Appendix C, or use `[tp]` for Table 5.
- **Not affected:** No overfull boxes, illegible tables or broken references were found. The Appendix B code listing does not wrap; it is checked against lines 221–239.

**12. Minor: the flowchart text is below legible print size.**
- **Location:** Figure 7, PDF p. 23.
- **Evidence:** At A4 print size the node text is roughly 4–5 pt; at 100 dpi it is barely readable. The caption acknowledges this ("can be zoomed") and points to Table 4.
- **Fix:** Render the flowchart in landscape (`pdflscape` is already loaded), or split it into two panels. Otherwise accept as is, since the caption gives a readable alternative.

**13. Minor: the abstract does not itself state the historical / reproduction-pending status.**
- **Location:** Abstract, `main.tex` L87–104.
- **Evidence:** The status box on the title page satisfies the policy. However, abstracts are often indexed or extracted without that box.
- **Fix:** Append to the abstract: "All values are existing results from a 30 September 2026 run; independent reproduction is pending."

**14. Minor: `content-coverage.md` has inaccuracies and omissions.**
- **Evidence:**
  - (a) "Sources and artifacts (13 bullets)": the original list has 12 bullets (L277–288).
  - (b) The dropped Input/Adaptation columns (Finding 1) are not recorded.
  - (c) The "Additions" section omits several new manuscript statements: the contributions list (L124–128), the multiplicity statement (L283–284), the cheap-baseline sentence (L371–372, which is correct against Table 5), the "worse than the one-hot CNN" clause (L375–376, also correct), the AI-coding-agents sentence (Finding 3) and the "favours strongly" phrase (Finding 6).
  - (d) Two original sentences were dropped without a note: "Check error by family." (original L182) and the FAQ advice "Compare CPU and accelerator outputs on your own setup before trusting them." (L23). Also dropped is the sentence on what `make_figures.py` and `describe_failures.py` produce (L263).
  - All section, table and figure numbers in the map otherwise match the PDF. I checked §§2.1–8, Tables 1–14, Figures 1–7 and Appendices A–E.
- **Fix:**
  - Correct the count and add the omissions.
  - Restore "Check error by family" at the end of §4.5.
  - Restore the CPU/accelerator advice at the end of the §4.6 device paragraph.
  - Add one sentence to Appendix A on what `make_figures.py` and `describe_failures.py` produce.

**15. Minor: §8 cites a disposition file that does not yet exist.**
- **Location:** `main.tex` L603–605.
- **Evidence:** `evidence/paper-migration/review-disposition.md` is absent at the time of this review.
- **Fix:** Create the file before the final build, or reword the sentence until it exists.

### Nits

**16. Nit: bibliography rendering.**
- The `note` fields print internal provenance in the reference list ("DOI as given in the companion NOTICE").
- The `uv` entry's author "Astral" is inferred from the URL domain; the original gives no author.
- **Fix:** Move the provenance notes to bib comments, which `references.bib` already uses at the top. Use `author = {{uv documentation}}` or omit the author.

**17. Nit: Table 8 formatting.**
- Read ranges lack thousands separators ("1154–22646") and show a fractional quartile edge ("100–314.75"), while the text says "100 to 315".
- **Fix:** Format the ranges with separators and round to integers, or add "(quartile edges; may be fractional)" to the caption.

**18. Nit: Table 9 caption order.**
- The caption says "Grouped and random…", but the columns are ordered random then grouped.

**19. Nit: Appendix A adaptation notes.**
- L615 says "`unzip` and `cd` joined", but the original already joined them (L219).
- The tutorial install command (`uv sync --extra test --extra notebook`, original L235) is omitted.

**20. Nit: wording that could read as a verification status.**
- Table 13 is headed "Independent verification", and §3.6 is titled "Execution, verification and provenance".
- **Fix:** Use "Independent mechanical checks by `verify.py`" so that nobody reads it as the policy's verification status.

**21. Nit: "22" is used for two different things.**
- §3.6 (L297) uses "all 22 method/split results" (11 methods × 2 splits), while §3.5 and Table 5 use "22 registered comparisons".
- **Fix:** Write "all 11 methods on both splits".

**22. Nit: the "45 of 49 records containing an ATG" figure is not in the archive.**
- **Location:** §4.5 L460.
- **Evidence:** `failures.json` `share_with_uatg` = 0.943 is the sub-library share (198/210), not the 49-record family. The ledger entry FAMILY cites only archive members, so this value is in fact article-only.
- **Fix:** Add `article/published-original.md` as evidence for this value in the FAMILY ledger entry.

**23. Nit: abstract phrasing.**
- "on a random split with 79.3% family overlap" should read "on a random split in which 79.3% of test records had a relative in training".

## Checks with no defect found

- **Numerical fidelity:**
  - Tables 1–2 match original Tables 2–3 and `metrics.json` in every cell. Training-mean random R² is −0.000 in the archive and printed 0.000, as in the original. Verdict labels are abbreviated exactly as in the original.
  - The +0.000 lower bound is exactly 0.0 in the archive and is correctly marked "no supported difference".
  - Table 3 matches the examples, and the SNV deltas (+0.17, +0.07, −0.06, +0.32; measured 0.665) are correct.
  - Seeds (0.533–0.580; 0.538–0.570; 0.559–0.570), counts (86/83, 118/87), base rates, cut-offs (7.402 / 7.360), ICC, 79.3%, 14,101 / 14.1%, 6.59 / 5.74, depth values, family values (1.134 / 0.405; 101; 49; 82%; 3.98 / 0.59; 0.314 / 0.723), parity (maximum 3.4e-8), embedding values, run time and step sum (3,415.2 s) all match.
  - Table 10 record counts sum to 100,017.
- **Status and claims:** No claim of verification, approval or human review appears, and §8 states that none has taken place. The exploratory status, the prior exposure of both test sets, seed and assay variability, and the "not equivalence" caveats are all preserved.
- **References:** Every bib entry corresponds to an original Sources item, or (for `uv`) to an original in-text link. Only Sample, Chu and mRNABench carry DOIs, and these match `NOTICE.md`; the Field and Welsh DOI is from the original. No years or authors are invented, apart from the "Astral" inference in Finding 16. The bibliography renders (17 entries, PDF p. 15).
- **Licences:** The figure licences (CC BY 4.0), GPL-3.0 / MIT header, AGPL-3.0, the "unknown" dataset licence and the unset companion licence are all stated accurately.
- **Privacy:** No personal paths or credentials appear in the manuscript, the generated tables or the migration evidence files.

## Author disposition

_To be completed by the paper author (see review-disposition.md)._
