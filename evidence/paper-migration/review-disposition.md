# Disposition of the independent review (`review.md`)

Author: paper-author agent (Claude Opus, `claude-opus-5-5`, session `5b2a6d85-2616-43fe-bdde-40dd448ad762`).
Date: 2026-10-06. `review.md` is unchanged (owned by the reviewer). All 23 findings were accepted; F12 was partly
addressed. After the fixes the manuscript was rebuilt with `make paper-imported` (24 pages; 0 LaTeX and 0 BibTeX
warnings; extraction cross-check 0 mismatches). The author re-rendered every page with `pdftoppm` at 40 dpi and
inspected pages 3, 4, 13, 17 and 18, where layout changed.

| Finding | Severity | Disposition |
|---|---|---|
| 1 Input/Adaptation columns dropped | major | Fixed: a key in the Table 1 caption gives input and adaptation for every method; recorded in `content-coverage.md`. |
| 2 Table 10 "Families" mislabelled | major | Fixed: columns renamed "Test families"; caption explains they count test-set families per sub-library and do not sum to 9,640 / 6,002. |
| 3 Unsupported AI-agent sentence in §8 | major | Fixed: sentence removed; §8 keeps the original disclosure plus the manuscript's drafting and review. |
| 4 Table 3 caption vs §7 | minor | Fixed ("only variable-region source sequences…; also holds the constant 780-nt tail"). |
| 5 Licence of the manuscript's own copy of the six records | minor | Fixed: §7 states that Table 3 and Supplement S1 reproduce them as the published article did and fall under the same owner decision. |
| 6 New literature generalisations | minor | Fixed: "We consider three options"; question phrasing; §4.2 now gives the ablation with its conditions. |
| 7 Reproduction box | minor | Fixed: the clean rerun "repeated a subset (Table 14)". |
| 8 Table 12 caption | minor | Fixed: ridge rows differ slightly; CNN rows are three seeds versus seed 0. |
| 9 "Worse than reference" attribution | minor | Fixed: attributed to the companion's verdict function. |
| 10 "historical" naming | minor | Fixed: Table 6 uses "random"; Table 13 caption explains verbatim check names; Figures 3–5 captions explain the panel label. |
| 11 Float placement | minor | Fixed: §3 starts on a new page after Figures 1–2; Table 4 placed `[H]` after §5.1; Appendix C no longer leaves a near-empty page. |
| 12 Flowchart legibility | minor | Partly addressed: the caption points to Table 4 as the readable equivalent and notes that the vector figure can be zoomed. Re-exporting the original figure with larger fonts is left as an owner decision. |
| 13 Abstract status | minor | Fixed: the abstract now ends by stating these are existing results and that reproduction is pending. |
| 14 Coverage map | minor | Fixed: 12 source bullets; dropped columns, new statements and restored sentences recorded; "Check error by family", the CPU/accelerator advice and the `make_figures.py`/`describe_failures.py` sentence restored. |
| 15 Missing disposition file | minor | Fixed: this file. |
| 16 Bibliography notes, uv author | nit | Fixed: provenance notes moved to the bib header comment; `uv` author set to "uv documentation". |
| 17 Table 8 formatting | nit | Fixed: integer edges with separators; caption notes rounding. |
| 18 Table 9 caption order | nit | Fixed ("Random and grouped"). |
| 19 Appendix A adaptation note | nit | Fixed: corrected description; the omitted notebook install command is named. |
| 20 "verification" wording | nit | Fixed: "mechanical checks" in §3.6 and Table 13. |
| 21 Two meanings of "22" | nit | Fixed: "all 11 methods on both splits". |
| 22 "45 of 49" source | nit | Fixed: the FAMILY ledger entry cites the article text for this value. |
| 23 Abstract phrasing | nit | Fixed. |

No experiment, inference, recomputation or network fetch was performed.
