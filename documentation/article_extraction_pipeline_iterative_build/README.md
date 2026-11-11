# Article Extraction Pipeline — Iterative Build

Turning DocLayout-YOLO boxes and Document AI OCR into articles (title, text,
front/back matter, series, continuations, index terms) with page positions,
plus each issue's imprint. The output is for topic modelling, classification,
juxtaposition analysis and publishing history. Pipeline code:
`pipeline/yolo_output_article_extraction/`; one volume end to end:
`pipeline/run_volume.py`.

## Where to read

| File | What it is |
|---|---|
| **`v2_pipeline.md`** | **the v2 pipeline, in full**: volumes, running, every extraction step and rule, output tables and columns, versions, known limits |
| `gold_article_list_annotation_guide.md` | the gold article list of the held-out test volumes (`evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv`, done) and how it is scored: `evaluation/evaluating_v2_article_extraction/evaluate_v2_with_gold.ipynb` → `evaluation/evaluating_v2_article_extraction/` |
| **`v1_to_v2_process.md`** | **how v2 was made**, step by step: v1 checked box by box, v2 rules decided and built, v2 re-checked, front end and freeze; every file used |
| `v1_rules.md` | v1's rules as evaluated (snapshot) |
| `v1_evaluation.md` | the v1 evaluation: method, conventions, results, findings |
| `v2_decisions.md` | decisions 0–10 with evidence and build status |
| `v2_recheck.md` | v2 re-checked against the v1 log (script numbers) |
| `v3_decisions.md` | the v3 decisions, built 2026-11-02, with evidence, status, v2-vs-v3 results and the held-out test (frozen as `extraction-v3`) |
| `v4_decisions.md` | the v4 rules, built 2026-11-03 to 11-06, with evidence, status and v3-vs-v4 results on the seen volumes (frozen as `extraction-v4`, with the held-out test) |
| `v5_decisions.md` | the v5 fixes A–H, built 2026-11-06, with evidence and results on the seen volumes (frozen as `extraction-v5`, with the held-out test) |
| `v6_decisions.md` | the v6 fixes to issue starts, issue numbers and the masthead record, built 2026-11-10 (not frozen, not yet tested on new texts) |

**Before this:** choosing and checking the layout and OCR models (Document AI,
DocLayout-YOLO, LayoutParser), the box study that chose DocLayout-YOLO, and the
original pilot plan are in `../establishing_layout_detection_AIs/`, e.g.
`../establishing_layout_detection_AIs/evaluation_error_log_documentation.md`.

## Versions

Each rules version has its own code tag, output folder and evaluation log, so
it's always clear which rules produced which output.

| Version | Git tag | Output folder | Evaluation | State |
|---|---|---|---|---|
| v1 | `extraction-v1` | `output/article_extraction/v1/` | `evaluation/evaluating_v1_article_extraction/reading_order_error_log.csv` | Frozen. 74 development pages: 1,068 boxes, 90.9% correct. |
| v2 | `extraction-v2` | `output/article_extraction/v2/` | re-check: `evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v2.csv`; test volumes: `evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv` (to annotate) | Frozen 2026-10-16. Test volumes run with it (see below). Development re-check: of 97 v1 errors, 29 fixed (script-checked), 58 changed, 10 unchanged; no v1-correct box broken. |
| v3 | `extraction-v3` | `output/article_extraction/v3/` | `evaluation/evaluating_v3_article_extraction/gold_article_list_test_v3.csv`, `v3_gold_comp_eval_summary.md` | Frozen 2026-11-02. Held-out test: 62/76 exact (82%). |
| v4 | `extraction-v4` | `output/article_extraction/v4/` | development: v2 and v3 gold lists; held-out: `evaluation/evaluating_v4_article_extraction/gold_article_list_test_v4.csv`, `v4_gold_comp_eval_summary.md` | Frozen 2026-11-06. Held-out test: 95/118 exact (81%). |
| v5 | `extraction-v5` | `output/article_extraction/v5/` | development: v2, v3 and v4 gold lists; held-out: `evaluation/evaluating_v5_article_extraction/gold_article_list_test_v5.csv`, `v5_gold_comp_eval_summary.md`, `evaluate_v5_with_gold.ipynb` | Frozen 2026-11-10. Held-out test: 68/87 exact (78%). |
| v6 | `extraction-v6` | `output/article_extraction/v6/` | development: v2–v5 gold lists | Frozen 2026-11-11. Issue starts and mastheads only. No held-out test yet. |

How versions are kept apart:
- **Code:** `PIPELINE_VERSION` in `run_extraction.py` decides the output folder.
  Frozen versions (`FROZEN_VERSIONS`) refuse to be written to.
- **Output:** each volume folder has a `run_info.json` with the version, git
  commit, whether the code had uncommitted changes, run date, volume, split
  and pages. Every table has `pipeline_version`, `volume` and `magazine`.
- **Evaluation logs:** each log belongs to one version's output and is never
  overwritten. `make_reading_order_template.py --version <v> --volumes … --out
  <new file>` builds a new one.

To re-run v1 exactly: `git checkout extraction-v1`, run the pipeline, then
`git checkout main`. v1's code writes to the old unversioned folder, so move
or compare its output by hand.

## Roadmap (agreed 2026-10-16)

1. **Documentation zone; tag `extraction-v1`.** *Done.*
2. **Build v2** from the decisions. *Done*; italics left out (Owen,
   2026-10-16).
3. **Re-check v2 on the development pages** against the v1 log. *Done*
   (`v2_recheck.md`).
4. **Front end for new volumes** (`pipeline/run_volume.py`; volumes in
   `magazine_rules_config.py`). *Done.*
5. **Freeze v2 and run the test volumes.** Tagged `extraction-v2`. Next:
   1. Run the held-out test volumes with frozen v2. *Done 2026-10-16:*
      - `penny_1836`, `saturday_1840`, `chambers_1839`, 24 issue pages each,
        all steps;
      - output in `output/article_extraction/v2/<volume>/`;
      - `run_info.json` records commit 2472eb78, which differs from the
        `extraction-v2` tag only in documentation (pipeline code checked
        identical before the run).
   2. Add v2 to `FROZEN_VERSIONS`; new work goes into v3. *Done.*
   3. Annotate a gold article list from the test pages (not from the
      output): `gold_article_list_annotation_guide.md`. *Done 2026-10-22* (94 rows). Scored by
      `evaluation/evaluating_v2_article_extraction/evaluate_v2_with_gold.ipynb`; results in
      `evaluation/evaluating_v2_article_extraction/v2_gold_comp_eval_summary.md`. These are the baseline
      numbers for the dissertation.
      - v3 candidates from the test results:
        - the Chambers 1840 masthead isn't recognised (its lines become
          articles and titles, splitting each issue's first article and
          losing issue numbers and dates);
        - illustration captions are taken as titles;
        - content is set aside as furniture (untitled poems);
        - the numbered-title series convention needs settling.
   4. The OCR evaluation: WER/CER on sampled passages against a literal
      transcription of what is printed (keeping the magazine's own
      spellings), plus an automatic check of words lost or duplicated
      between boxes.

**Later:**
- illustration descriptions;
- scale-up to all volumes (1832–1844);
- the volume index as a series source;
- adding checked pages to `verified_pages.json`.

## Running

```
python pipeline/run_volume.py --volume penny_1836                                 # a volume, all steps
python pipeline/yolo_output_article_extraction/run_extraction.py --volume penny   # extraction only
python pipeline/yolo_output_article_extraction/check_verified.py                 # regression check
```

See `v2_pipeline.md` §3 for environments and output.
