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
