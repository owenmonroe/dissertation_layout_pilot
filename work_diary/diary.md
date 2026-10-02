# Work Diary

## 2026-09-28

- Built the `layoutparser-env` conda environment (Python 3.11, Detectron2 CPU build,
  LayoutParser, OpenCV, Pillow) for the Detectron2/LayoutParser side of the pilot.
- Wrote a PDF-to-PNG rasterizer (300 DPI) since Detectron2/OpenCV can't read PDFs directly.
- Tested the environment on one page; found LayoutParser's built-in model download links
  (Dropbox) are dead, switched to a community Hugging Face mirror for weights.
- Tried Newspaper Navigator (redundant — only caught an illustration PrimaLayout also
  catches) and PubLayNet (wrong domain — found ~nothing on a historical scan); both dropped.
- Chose **PrimaLayout** (trained on historical European document layouts) as the model —
  correctly picked up text columns, images, and separator lines on the test page.
- Compared score thresholds (0.5 / 0.7 / 0.75) by eye, settled on **0.7** for the main run.
- Built a batch pipeline and applied PrimaLayout (threshold 0.7) across full sampled issues
  of all three magazines — penny (26p), chambers (24p), saturday (24p) — writing annotated
  page images + JSON box data per page.
- Reorganized output naming into a consistent `<mag>_page_NNN` scheme with per-magazine
  folders, and updated the pipeline scripts to generate that structure natively.
- Ran a small follow-up experiment: reprocessed one page per magazine at a lower 0.5
  threshold to compare against the 0.7 baseline.

## 2026-09-29

- Built the `doclayoutyolo-env` venv (plain Python 3.10, not conda -- pure PyTorch/pip
  wheels, no compiled extensions) and a one-page sanity check for DocLayout-YOLO
  (DocStructBench checkpoint, zero-shot, MPS/Apple GPU inference).
- Kept the 0.2 confidence threshold from the one-page check, built a batch pipeline,
  and applied DocLayout-YOLO across all three magazines' full sampled issues.
- Caught and fixed a git mistake: the entire `doclayoutyolo-env` venv (~34,000 files)
  had been committed by accident. Amended the (unpushed) commit to strip it out and
  added `venv_build_test/*-env/` to `.gitignore` going forward.
- Set up Google Cloud (project, billing, Document AI API, `gcloud` auth via
  Application Default Credentials) to try Google Document AI.
- Tried a Document AI **Layout Parser** processor first -- dropped it after finding
  it misclassified a two-column page as a single table and left most nested blocks
  without a bounding box (a known open issue on Google's side, not fixable via config).
- Switched to a Document AI **Document OCR** processor instead -- reliable
  paragraph-level boxes on every block, plus full OCR text bundled in for free.
  Built a batch pipeline and applied it across all three magazines' full sampled
  issues (confirmed $0.00 cost -- well under the 1,000 free pages/month tier).

**Observations:**
- DocLayout-YOLO's boxes look stronger/cleaner individually, but it segments at
  paragraph/indent level rather than article level -- grouping paragraphs into whole
  articles would likely require detecting title boxes, then establishing reading
  order (cluster boxes into columns by x-position, sort top-to-bottom within each
  column) before grouping everything between one title and the next.
- Google Document AI's block grouping fails to separate short "filler" items from
  each other or from a preceding long article -- e.g. lower-right corner of
  `output/penny_google/penny_page_003_docai.png` (the "FAIR PLAY" article merged
  with the following "Changes of Manners" / "Animal Sagacity" filler items into one
  box) and `output/saturday_google/saturday_page_011_docai.png` (a long piece merged
  with the following "HUMMING BIRDS." filler item). Separating short filler/ephemera
  from genuine long-form articles is key to this project, so this is a real
  limitation to account for.

**Next steps plan:** take just the first 3 pages from each magazine --
1. Hand-develop a "perfect" chunking with labels (gold standard) for those pages.
2. Count false positives / blocking issues from each of the three models against
   that gold standard, using a shared error taxonomy so counts are comparable
   across models:
   - **Merge** -- one box contains multiple logical units (e.g. Google merging a
     filler item into the preceding article)
   - **Split** -- one logical unit fragmented across multiple boxes (e.g. YOLO
     splitting a single article into per-paragraph boxes)
   - **Under-coverage** -- box doesn't fully reach the region, cuts off text
     (e.g. Prima's boxes falling short of the full column/paragraph)
   - **Misplacement** -- box crosses columns oddly or spans unrelated content
     (e.g. Google's boxes stretching awkwardly across columns)
   - **Missed region** -- no box at all where one should be (e.g. Google not
     boxing images/illustrations at all)
   - **Mislabel** -- right box, wrong category (e.g. YOLO reading an epigraph
     or block quote as a title)
3. Run OCR extraction from each model's boxes, attempt a stitching algorithm.
4. Evaluate text errors across articles by comparing against the original text
   directly (manual read-through, not just automated metrics).

- Added a `#N` index label to every box in all three models' annotated output
  images, so a box spotted visually can be looked up directly in that page's
  JSON (see `documentation/box_index_ordering.md`) -- and set up
  `evaluation/error_log_template.csv` to log errors against the taxonomy above
  during the hand-annotation pass.

## 2026-09-30

- Copied the 9 evaluated page rasters (first 3 pages per magazine) into
  `evaluation/groundtruth_texts/` as `<mag>_page_NNN_groundtruth.png`, as working
  copies for building the gold-standard chunking.
- Started filling in `evaluation/error_log_template.csv` box-by-box, working
  interactively with Claude Code: Claude prompts magazine / page / model / box `#N`,
  I give a verdict, then a note (or `0` for none), and Claude appends the row.
  Order: magazine (chambers -> penny -> saturday), page 1-3, model
  (Google -> PrimaLayout -> DocLayout-YOLO).
- Verdicts are the error taxonomy (merge, split, under-coverage, misplacement,
  missed region, mislabel) plus **good** and **good abandon** (correct box around page
  furniture) so correct vs incorrect boxes can be counted, not just errors. Also
  used **misplacement abandon** for misplaced boxes around furniture / empty margin.
- Conventions settled along the way: several errors decided together on one box go
  in one row joined with `; ` (e.g. `split; missed region`, ordered consistently
  so `split; mislabel` is always written that way); an error noticed later for an
  already-logged box gets a second row for the same index (mostly under-coverage of
  titles / bylines / masthead text); notes record what the box covers (masthead,
  byline, header title, page number) and how it fails (e.g. "cut at indent", "not
  full column").
- Found the PrimaLayout / YOLO `#N` labels unreadable in places: masthead boxes at
  the top edge had labels drawn off-image, and stacked labels on duplicate boxes.
  Wrote `evaluation/draw_eval_boxes.py` to paste larger `#N` tags onto the
  untouched model output images (boxes kept exactly as the models output them;
  near-identical boxes share one tag, e.g. `#7 | #12`). Indexes unchanged.
- Found DocLayout-YOLO emits duplicate boxes: its YOLOv10 post-processing ranks
  every (box, class) pair, so one region can be kept as both plain text and title,
  and with no NMS near-identical boxes both survive the 0.2 threshold. Logged each
  copy separately with "doubled on X" / "double of X" notes so results can be
  reported with and without duplicates.
- Caught a few misreads along the way (wrong box read under overlapping labels, a
  non-existent index logged, a mislabel attributed to the wrong copy of a
  duplicate) and corrected the rows -- checking box coordinates in the JSON when a
  tag is ambiguous.
- Patterns so far (chambers): splitting at paragraph indents is by far the most
  common error across all three models; Google also draws misplaced boxes
  stretching across columns and small random word boxes; PrimaLayout's boxes often
  miss the top/bottom of a column and skip titles/bylines; YOLO is consistently
  correct on page furniture and masthead parts but splits columns at every indent.
- Finished all 9 chambers page/model combinations (168 boxes, every index checked
  against the JSON). Penny and saturday still to do -- resume at penny p1 Google
  box 0. Documented the process in
  `documentation/evaluation_error_log_documentation.md`.

## 2026-10-01

- **Indexing boxes:** cleaned up the eval images so every box can be identified.
  `draw_eval_boxes.py` puts a large white `#N` tag on each PrimaLayout / YOLO box
  (index = position in the JSON), and now also removes the pipeline's small
  magenta `#N` labels from the YOLO pages. Those came from our own
  `save_annotated_image`, not from YOLO, and doubled up with the white tags. Only
  the magenta pixels are replaced; YOLO's boxes, labels and JSON are untouched.
- **Error log:** finished penny and saturday by hand, then checked coverage against
  the JSON: all 27 page/model combinations complete (495 rows, 482 boxes), no
  missing or invalid indexes.
- **Analysis:** built `evaluation/error_analysis.ipynb` (total errors, errors by
  type, errors by magazine, per page, error causes from notes, content vs
  furniture) plus a fragmentation check against my gold-standard boxes in
  `evaluation/groundtruth_texts/`.

**Key findings:**
- % of boxes correct: Document AI 55.6%, YOLO 54.5%, PrimaLayout 41.4%. All three
  box page furniture (headers, page numbers) almost perfectly, which inflates
  these. On content boxes only: YOLO 35.6%, Document AI 30.9%, PrimaLayout 18.8%.
- **Splitting is the dominant error** for every model (61% of Document AI's
  errors, 73% of PrimaLayout's, 92% of YOLO's). The notes show why: ~150 split
  errors mention indents and ~120 columns. The models segment at paragraph level,
  while the unit I want is the whole article column.
- **Fragmentation** (content boxes / gold boxes, all 9 pages): Document AI 1.54,
  PrimaLayout 1.60, YOLO 2.10 (1.95 without duplicates). YOLO draws about 2 boxes
  per true region.
- **Chambers is the hardest magazine to box**: 0.68 errors per box vs 0.49 penny
  and 0.45 saturday, and fragmentation 1.8-2.6 across models. Chambers p3 is the
  worst page (5 gold content boxes; YOLO drew 19).
- **YOLO tracks the page well but splits it:** almost no missed regions (1) or
  misplacements (2). Its errors are nearly all splits stacked within the right
  column, plus easy-to-remove duplicates, so merging boxes in post-processing
  could recover a lot.
- **PrimaLayout misses regions:** 15 missed regions and 9 under-coverage (column
  tops/bottoms, titles, bylines). This is lost text, which merging can't fix.
- **Document AI misplaces boxes:** 15 misplacements, boxes stretching across
  columns, which then cut up neighbouring boxes (16 errors noted as caused by
  another misplaced box). It also merges short filler items into articles
  (saturday p3: 7 content boxes vs 13 gold).
- Leaning towards YOLO plus a box-merging step for article extraction, rather than
  picking the model with the fewest raw errors. Caveat: only 3 pages per magazine.
