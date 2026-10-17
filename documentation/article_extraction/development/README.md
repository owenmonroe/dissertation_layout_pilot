# From v1 to v2: How the Rules Were Checked and Rebuilt

The working record of how the first article-extraction pipeline (v1) was
evaluated, how the v2 rules were decided and built, and how v2 was re-checked.
The pipeline itself is described in `../v2_pipeline.md`.

**Development pages:** all of this used the 1832 build sample: the first
three issues of the Penny Magazine, the Saturday Magazine and Chambers's
Edinburgh Journal (74 pages; volumes `penny`, `saturday`, `chambers`, PDFs in
`build_texts/`). The held-out test issues (`test_texts_extraction/`) were not
looked at.

**Background:** before this work, the layout model was chosen by a box-level
evaluation of three models. See `../../evaluation_error_log_documentation.md`,
`evaluation/boxing_error_log_template.csv` and
`evaluation/error_analysis.ipynb`. DocLayout-YOLO was chosen.

## The steps

### 1. Build v1 and fix its rules in writing
- **Built** v1 (YOLO boxes + Document AI words → articles), magazine by
  magazine.
- **Checked by hand** a few pages per magazine. These were stored as a
  regression check: `pipeline/yolo_output_article_extraction/verified_pages.json`,
  checked by `check_verified.py`.
- **Wrote down** the rules exactly as evaluated, and never edited them:
  `v1_rules.md`.
- **Tagged the code** `extraction-v1`. Its output is frozen in
  `output/article_extraction/v1/`.

### 2. Annotate v1's output box by box (the reading-order evaluation)

**The template.** `evaluation/make_reading_order_template.py --version v1`
wrote one row per box the pipeline placed. Each row has the reading order,
role, article and the box's first and last words, pre-filled as `ok`.

**The images.** Each row matches a labelled box on that page's check image,
`output/article_extraction/v1/<mag>/reading_order/`.

**The log.** Owen went page by page and changed only the errors: verdict,
error type (role, merge, split, misattached, misplacement, missed) and notes.
Rows were added for anything set aside wrongly. The result is
`evaluation/reading_order_error_log.csv`: 1,090 rows, of which 1,068 boxes
were evaluated and 22 were excluded as duplicate scan pages. It is never
overwritten.

**Write-up:** `v1_evaluation.md` has the method, the conventions agreed
along the way, the results (90.9% of boxes correct; 97 errors; no
reading-order errors) and the findings by error type.

### 3. Decide the v2 rules
`v2_decisions.md` holds decisions 0–10. Each has the decision, its evidence
from the log (magazine, page, box) and a status (decided → built).

| Decision | Topic |
|---|---|
| 0 | versioned output (each version in its own folder) |
| 1 | front and back matter |
| 2 | sign-offs |
| 3 | series and continuations |
| 4 | fillers (printed rules, volume index) |
| 5 | run-in heads |
| 6 | captions, figures, tables |
| 7 | imprint and editorial notices |
| 8 | text recovery |
| 9 | duplicate scan pages |
| 10 | metadata |

Principles Owen set while deciding:
- **General rules:** rules must generalise to many more and more complex
  volumes, and must not overfit these pages. Each rule rests on a printing
  convention; some misses are acceptable.
- **No hand fixes:** no hand-entered facts in the extraction. The volume
  index is the route for cases no rule can see.
- **Script numbers only:** every evaluation number comes from a script.
- **Low priorities:** subsections and tables are low importance, so no rules
  just for them. Tables are labelled and kept out of the text.
- **Rejected: an LLM boundary check.** Too costly and vague.

### 4. Build v2, one decision at a time
For each decision:
1. Change the code.
2. Re-run all three development volumes and `check_verified.py`.
3. Compare every logged box with v1's output to catch regressions. Any box
   logged ok that changed was investigated and either justified or fixed.
4. Set the decision's status to built in `v2_decisions.md`, with what was
   fixed and what was left.

New modules:

| Module | What it does | Decision |
|---|---|---|
| `series.py` | series and continuations | 3 |
| `rules.py` | printed-rule detection | 4 |
| `volume_index.py` | the index check | 4 |
| `duplicates.py` | duplicate scan pages | 9 |

`articles.py`, `text.py`, `layout.py` and `run_extraction.py` were extended
for the other decisions.

### 5. Re-check v2 against the v1 log (roadmap step 3)
`evaluation/compare_versions.py`, or `evaluation/compare_versions.ipynb`
(same code, tables shown cell by cell), looks up every logged box in v2's
output and gives an outcome:
- **`fixed`:** checked by the script for merge, split, misplacement and
  missed errors;
- **`changed`:** the box differs but needs annotation to confirm;
- **`unchanged`:** the error persists.

It writes `evaluation/reading_order_v1_vs_v2.csv` and `..._summary.md`.

**Result** (`v2_recheck.md`), of the 97 logged errors:
- 29 fixed;
- 58 changed;
- 10 unchanged.

Of the 971 boxes logged ok, none was broken. Logged boxes correct: v1 90.9%;
v2 between 93.5% (counting every `changed` as wrong) and 99.1% (counting it
as fixed). The rules were written from these pages, so this shows the
decisions were carried out, not v2's accuracy on new text.

### 6. Front end and freeze (roadmap step 4)
- **Front end:** `pipeline/run_volume.py` runs any volume from its PDF
  (volumes in `magazine_rules_config.py`).
- **Freeze:** the code was tagged `extraction-v2`.
- **Next:** the held-out test volumes are run with frozen v2 and annotated.
  Those are the baseline numbers (roadmap step 5).

## Files

| File | Role |
|---|---|
| `v1_rules.md` | v1's rules as evaluated (snapshot) |
| `v1_evaluation.md` | the v1 evaluation: method, conventions, results, findings |
| `v2_decisions.md` | decisions 0–10 with evidence and build status |
| `v2_recheck.md` | v2 re-checked against the v1 log |
| `evaluation/reading_order_error_log.csv` | the v1 annotation log (never overwritten) |
| `evaluation/make_reading_order_template.py` | builds an annotation log for a version's output |
| `evaluation/compare_versions.py`, `.ipynb` | re-checks a version against a log |
| `evaluation/reading_order_v1_vs_v2.csv`, `..._summary.md` | the re-check's output |
| `output/article_extraction/v1/` | frozen v1 output (what the log describes) |
| `pipeline/yolo_output_article_extraction/verified_pages.json`, `check_verified.py` | the regression check |
