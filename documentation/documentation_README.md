# Documentation — Master Overview

**Project:** turning scanned nineteenth-century magazines into structured
**articles** for a dissertation. The magazines are the *Penny Magazine*, the
*Saturday Magazine* and *Chambers's Edinburgh Journal*, 1832–1844, from
HathiTrust scans. Each article gets:
- its title and text;
- its sources, bylines and notes (front and back matter);
- series and continuation links;
- index terms;
- its exact place on the page.

Each issue's imprint is kept as well. The articles feed topic modelling,
classification, juxtaposition analysis (what was printed next to what) and
publishing history.

## Overall points

- **Models find, rules decide.** Off-the-shelf AI models draw the layout boxes
  (DocLayout-YOLO) and read the words (Google Document AI). A rule-based
  pipeline written for this project decides everything after that: what is
  a title, where an article starts and ends, what is a source line, what
  belongs to a series.
- **Rules follow printing conventions,** not particular pages (a dash after a
  run-in head, centred rules between items, "To be continued"). That keeps
  them working on volumes they weren't written from. Some misses are
  accepted rather than adding brittle fixes.
- **Build texts and test texts are kept apart.**
  - Rules are developed on the 1832 *build texts* (the first three issues of
    each magazine).
  - Each pipeline version is then frozen and measured on held-out *test
    texts* from later volumes. These are annotated by hand from the printed
    pages, without seeing the output.
- **Every number comes from a script.** Evaluation results are computed and
  saved by scripts and notebooks, never judged by eye.
- **Versions are tagged and frozen.** Each pipeline version has a git tag, its
  own output folder and its own evaluation, and frozen output is never
  overwritten.

## The stages

### 1. Comparing layout AIs (done)

**Models compared on the build texts:**
- **Google Document AI** (Document OCR: layout and text);
- **LayoutParser / PrimaLayout**, a model trained on historical European
  documents. Newspaper Navigator and PubLayNet were tried first and dropped;
- **DocLayout-YOLO**, zero-shot.

**How:** every box each model drew on 9 pages (3 per magazine) was judged by
hand in a box-level error log (merge, split, under-coverage, misplacement,
missed region, mislabel), and compared with hand-drawn gold boxes.

**Findings:**
- On content boxes, YOLO was correct most often: 35.6%, against Document AI
  30.9% and PrimaLayout 18.8%.
- All three split article columns at paragraph level.
- **YOLO** tracks the page well and almost never misses text; its errors are
  mostly splits, which rules can repair.
- **PrimaLayout** misses regions, so text is lost.
- **Document AI** draws boxes across columns.

**Decision:** DocLayout-YOLO for layout, plus Document AI's OCR for the words.

Docs: `establishing_layout_detection_AIs/`.

### 2. Article extraction v1: Document AI + YOLO + rules (done)

- **Built:** the first rule-based pipeline (YOLO boxes + Document AI words →
  articles), tagged `extraction-v1`.
- **Evaluated** box by box on all 74 build pages for reading order and
  article assignment: 1,068 boxes, **90.9% correct**, no reading-order
  errors.
- **The 97 errors became 10 decisions for v2.** Mostly they were front/back
  matter in the wrong place, fillers merged into the item before them,
  series headings joined to titles, and tilt fragments.

Docs: `article_extraction_pipeline_iterative_build/` (`v1_rules.md`,
`v1_evaluation.md`, `v2_decisions.md`).

### 3. Article extraction v2: Document AI + YOLO + rule scripts (done)

**Built:** the 10 decisions, as new rule scripts:
- front and back matter;
- series and continuations;
- printed-rule detection;
- the volume index check;
- duplicate scan pages;
- text recovery;
- tables;
- imprints.

**Re-checked** against the v1 log: of 97 errors, 29 fixed (script-checked),
58 changed and 10 unchanged, with no correct box broken.

**Front end and freeze:** a one-command front end for new volumes
(`pipeline/run_volume.py`), then the code was frozen as `extraction-v2`.

**Tested on held-out issues** from Penny 1836, Saturday 1840 and Chambers 1840
(three issues each), scored against Owen's gold article list of 96 rows:
- **72%** of items extracted exactly;
- boundary recall **93%** (v2 rarely misses where an article starts);
- boundary precision **66%** (it over-splits);
- titles 81%;
- all imprints captured.

**Main lessons for v3:**
- The Chambers 1840 masthead isn't recognised, so it splits articles and
  loses issue numbers and dates.
- Illustration captions are taken as titles.
- Untitled poems are set aside as page furniture.

Docs: `article_extraction_pipeline_iterative_build/` (`v2_pipeline.md`,
`v1_to_v2_process.md`, `gold_article_list_annotation_guide.md`).

### 4. Article extraction v3: Document AI + YOLO + rule scripts (done)

**Built** from the v2 test findings, with the v2 test issues as build texts
(`v3_decisions.md`), and frozen as `extraction-v3`.

**Tested on held-out issues** from Penny 1838, Saturday 1834 and Chambers 1843
(three issues each, 85 gold rows, 76 scored items). First score, before any
gold corrections:
- **82%** of items extracted exactly;
- boundary recall **93%**, boundary precision **72%** (it over-splits);
- titles 90%, front matter 78%, back matter 68%, series 29%;
- issue numbers and dates 100%; 8 of 9 imprints.

The score on the v2 test issues (94% exact) is not a held-out result, because
v3 was built on them.

## To do

- **Article extraction v4:** fix the v3 test findings, chiefly inner headings
  read as new articles. The v3 test texts have now been seen.
- **OCR evaluation:** WER/CER on sampled passages against a literal
  transcription of what is printed, plus a check for words lost or
  duplicated between boxes.
- **Final pipeline:** apply it to all volumes, 1832–1844.

## Folder architecture

```
dissertation_layout_pilot/
├── build_texts/                      1832 build PDFs (rules developed on these); images/ = page rasters (git-ignored)
├── documentation/
│   ├── documentation_README.md       this page
│   ├── establishing_layout_detection_AIs/          stage 1: the models, their setup, the box evaluation
│   └── article_extraction_pipeline_iterative_build/ stages 2–3 and on: the article pipeline, version by version
├── evaluation/
│   ├── evaluating_layout_detection/      stage 1: box error log, analysis notebook, gold boxes, eval images
│   ├── evaluating_v1_article_extraction/  stage 2: reading-order error log, v1-vs-v2 comparison
│   ├── evaluating_v2_article_extraction/  stage 3: gold article list, scoring script + notebook, results,
│   │                                     test_texts_extraction_v2/ (held-out test PDFs)
│   └── evaluating_v3_article_extraction/  stage 4: v3 gold list, results, test_texts_extraction_v3/ (held-out test PDFs)
├── output/
│   ├── output_images_json_establishing_layout_AIs/  model output on the build texts (Document AI, YOLO, PrimaLayout)
│   ├── output_images_json_v2_article_extraction/    model output on the v2 test texts (Document AI, YOLO)
│   ├── output_images_json_v3_article_extraction/    model output on the v3 test texts (Document AI, YOLO)
│   └── article_extraction/<version>/<volume>/       extracted articles: CSVs, SQLite, check images, figures
├── pipeline/
│   ├── run_volume.py, run_doclayoutyolo_batch.py, run_docai_batch.py, run_prima_batch.py, …
│   └── yolo_output_article_extraction/   the rule-based article pipeline (config, layout, text, articles, series, …)
├── venv_build_test/                  environment setup checks and pdf_to_images.py (environments themselves git-ignored)
├── models/                           downloaded model weights (git-ignored)
└── work_diary/diary.md               dated working log
```

## Other documentation pages

**Stage 1, `establishing_layout_detection_AIs/`**

| Page | What it covers |
|---|---|
| `pilot_steps.md` | the original pilot plan |
| `docai_model_documentation.md` | Document AI: processor, setup, cost, runs, limitations |
| `doclayoutyolo_model_documentation.md` | DocLayout-YOLO: model, settings, setup, runs |
| `layoutparser_model_documentation.md` | LayoutParser / PrimaLayout: model, settings, the models dropped |
| `box_label_taxonomy.md` | the box labels everything was mapped to |
| `box_index_ordering.md` | what the `#N` box labels on eval images mean |
| `evaluation_error_log_documentation.md` | the box-level error log: method, conventions, eval images |

**Stages 2 onward, `article_extraction_pipeline_iterative_build/`**

| Page | What it covers |
|---|---|
| `README.md` | the pipeline's plan: versions, roadmap, how to run |
| `v2_pipeline.md` | the v2 pipeline in full: every step, rule and output column |
| `v1_to_v2_process.md` | how v2 was made, step by step, with every file used |
| `v1_rules.md` | v1's rules as evaluated (snapshot) |
| `v1_evaluation.md` | the v1 evaluation: method, conventions, results |
| `v2_decisions.md` | the 10 decisions behind v2, with evidence and status |
| `v2_recheck.md` | v2 re-checked against the v1 log |
| `v3_decisions.md` | the v3 decisions, with evidence and v2-vs-v3 results |
| `gold_article_list_annotation_guide.md` | how the test texts were annotated, and how they are scored |
