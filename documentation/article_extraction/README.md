# Article Extraction — Documentation

Turning DocLayout-YOLO boxes and Document AI OCR into articles (title, text,
front/back matter, series, continuations) with page positions, for topic
modelling, classification and juxtaposition analysis. Pipeline code:
`pipeline/yolo_output_article_extraction/`.

## Files

| File | What it is |
|---|---|
| `README.md` | this page: file map, versions, roadmap |
| `v1_rules.md` | the pipeline's rules **as evaluated** (snapshot, never edited) |
| `v1_evaluation.md` | the reading-order evaluation: method, conventions, results, findings |
| `v2_decisions.md` | decisions and new rules from the evaluation, each with evidence and status |
| `v2_recheck.md` | v2 re-checked against the v1 log (roadmap step 3): method and the script's numbers |
| `evaluation/reading_order_error_log.csv` | the error log itself (1,090 rows), built by `evaluation/make_reading_order_template.py` |
| `evaluation/compare_versions.py` | looks up every logged box in another version's output; writes `evaluation/reading_order_v1_vs_v2.csv` and `..._summary.md` |
| `evaluation/compare_versions.ipynb` | runs the same comparison and shows the tables: outcomes by error type and magazine, before/after % correct, regressions, persisting errors, page lookup |

Related: the box study that chose DocLayout-YOLO,
`../evaluation_error_log_documentation.md`.

## Versions

Each rules version has its own code tag, output folder and evaluation log, so
it's always clear which rules produced which output.

| Version | Git tag | Output folder | Evaluation log | State |
|---|---|---|---|---|
| v1 | `extraction-v1` | `output/article_extraction/v1/` | `evaluation/reading_order_error_log.csv` | Frozen. Evaluated on the 74 development pages (2026-10-14 to 2026-10-16): 1,068 boxes, 90.9% correct, no reading-order errors. Rules: `v1_rules.md`. |
| v2 | `extraction-v2` (when frozen) | `output/article_extraction/v2/` | re-check: `evaluation/reading_order_v1_vs_v2.csv` (`v2_recheck.md`); test issues in step 5 | All decisions in `v2_decisions.md` built (italics deferred). Re-checked on the development pages (`v2_recheck.md`): of 97 v1 errors, 29 fixed (script-checked), 58 changed (to annotate), 10 unchanged. |

How versions are kept apart:
- **Code:** `PIPELINE_VERSION` in `run_extraction.py` decides the output folder.
  Frozen versions (`FROZEN_VERSIONS`) refuse to be written to.
- **Output:** each magazine folder has a `run_info.json` (version, git commit,
  whether the code had uncommitted changes, run date, pages). v1's were
  written retroactively. Every v2 table row has a `pipeline_version` column.
- **Evaluation logs:** each log belongs to one version's output and is never
  overwritten. `make_reading_order_template.py --version <v> --out <new file>`
  builds a new one.

To re-run v1 exactly: `git checkout extraction-v1`, run the pipeline, then
`git checkout main`. v1's code writes to the old unversioned folder, so move
or compare its output by hand.

## Roadmap (agreed 2026-10-16)

1. **Set up this documentation zone and tag `extraction-v1`.** *Done
   2026-10-16.* Also done: version folders for output (v1 moved unchanged
   into `output/article_extraction/v1/`), run records, the `pipeline_version`
   column.
2. **Build v2** from `v2_decisions.md`:
   - front/back matter fields;
   - the sign-off rules;
   - series and continuations;
   - filler items (printed rules plus the volume index);
   - the imprint rule;
   - text recovery (side-edge strips, single lines, junk and watermark boxes);
   - duplicate scan pages;
   - tables.

   Update each decision's status as it's built. *Done 2026-10-16*, except
   italics (Document AI style information; check the cost first).
3. **Re-check v2 on the development pages,** mostly automatically by comparing
   the new output with the error log. The v1 numbers are the "before" for
   showing improvement. *Done 2026-10-16* (`v2_recheck.md`).
4. **Build the front end for new volumes.** *Done 2026-10-16.*
   - `pipeline/run_volume.py --volume <key>` runs PDF → 300 DPI page images →
     DocLayout-YOLO (`doclayoutyolo-env`) → Document AI (`docai-env`) →
     extraction, each step in its own environment. Pages already done are
     skipped.
   - Volumes are listed in `magazine_rules_config.py` (`VOLUMES`). Each one
     gives its magazine (which decides the rules), PDF, issue pages, index
     pages, and split: `build` for the 1832 development samples in
     `build_texts/`, `test` for the held-out issues in
     `test_texts_extraction/` (penny_1836, saturday_1840, chambers_1839).
   - Every output table has `volume` and `magazine` columns.
5. **Freeze v2 and run the test issues.** Tag `extraction-v2`, run fresh
   later-year issues (one per magazine, e.g. 1836, 1840, 1843) that no rule
   was tuned on, and annotate them once. Those are the baseline numbers for
   the dissertation. Annotate them with:
   - the reading-order log, using `make_reading_order_template.py`;
   - the OCR evaluation: WER/CER against a literal transcription of what is
     printed, keeping the magazine's own spellings, on sampled passages;
     plus an automatic completeness check of words lost or duplicated between
     boxes.

**Later:**
- **Volume index** as a check and title source (part of step 2 for fillers);
- illustration descriptions;
- scale-up to all volumes (1832–1844), with a `volume` column and
  volume-unique article IDs;
- adding checked pages to `verified_pages.json` so the quick regression check
  guards more pages.

## Running the pipeline

```
python pipeline/run_volume.py --volume penny_1836          # a new volume, all steps
python pipeline/yolo_output_article_extraction/run_extraction.py --volume penny   # extraction only
python pipeline/yolo_output_article_extraction/check_verified.py
```

- **Output:** `output/article_extraction/<version>/<volume>/` (CSVs, `figures/`,
  `reading_order/` check images, `run_info.json`) and
  `output/article_extraction/<version>/articles.sqlite` (tables `pages`,
  `articles`, `regions`).
- **Per-magazine settings:**
  `pipeline/yolo_output_article_extraction/magazine_rules_config.py`.
- **Python:** any Python with pandas and Pillow works.
