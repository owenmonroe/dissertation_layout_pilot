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
| `evaluation/reading_order_error_log.csv` | the error log itself (1,090 rows), built by `evaluation/make_reading_order_template.py` |

Related: the box study that chose DocLayout-YOLO,
`../evaluation_error_log_documentation.md`.

## Versions

| Version | Git tag | State |
|---|---|---|
| v1 | `extraction-v1` | Evaluated on the 74 development pages (2026-10-14 to 2026-10-16): 1,068 boxes, 90.9% correct, no reading-order errors. Rules: `v1_rules.md`. |
| v2 | (`extraction-v2` when frozen) | In progress: the decisions in `v2_decisions.md`. |

To re-run v1 exactly: `git checkout extraction-v1`, then run the pipeline
(below), then `git checkout main`.

## Roadmap (agreed 2026-10-16)

1. **Set up this documentation zone and tag `extraction-v1`.** *Done
   2026-10-16.*
2. **Build v2** from `v2_decisions.md`:
   - front/back matter fields;
   - the sign-off rules;
   - series and continuations;
   - filler items (printed rules plus the volume index);
   - the imprint rule;
   - text recovery (side-edge strips, single lines, junk and watermark boxes);
   - duplicate scan pages;
   - tables.

   Update each decision's status as it's built.
3. **Re-check v2 on the development pages,** mostly automatically by comparing
   the new output with the error log. The v1 numbers are the "before" for
   showing improvement.
4. **Build the front end for new volumes:** PDF → 300 DPI page images →
   DocLayout-YOLO (in `doclayoutyolo-env`) → Document AI → extraction, for any
   volume, with a volume ID. Reuse `pipeline/run_doclayoutyolo_batch.py` and
   `pipeline/run_docai_batch.py`.
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
python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny
python pipeline/yolo_output_article_extraction/check_verified.py
```

- **Output:** `output/article_extraction/<mag>/` (CSVs, `figures/`,
  `reading_order/` check images) and `output/article_extraction/articles.sqlite`
  (tables `pages`, `articles`, `regions`).
- **Per-magazine settings:**
  `pipeline/yolo_output_article_extraction/magazine_rules_config.py`.
- **Python:** any Python with pandas and Pillow works.
