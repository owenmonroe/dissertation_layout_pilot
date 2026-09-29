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
   that gold standard.
3. Run OCR extraction from each model's boxes, attempt a stitching algorithm.
4. Evaluate text errors across articles by comparing against the original text
   directly (manual read-through, not just automated metrics).
