# LayoutParser / PrimaLayout Pilot — Model Documentation

## Model used

**PrimaLayout** — a Detectron2 Mask R-CNN (R-50-FPN-3x backbone) model, loaded through the
LayoutParser library. Trained on the PRImA Layout Analysis dataset, which consists of
historical European document scans — this is a much closer domain match for scanned
19th-century magazines than modern document datasets.

Detected classes: `TextRegion`, `ImageRegion`, `TableRegion`, `MathsRegion`,
`SeparatorRegion` (a printed rule/divider line, e.g. between columns), `OtherRegion`.

Two other models were tried first and dropped:
- **Newspaper Navigator** (trained on Chronicling America historical U.S. newspapers) —
  found only the same illustration PrimaLayout already finds, nothing else. Redundant, cut.
- **PubLayNet** (trained on modern scientific-paper layouts) — found effectively nothing on
  a tilted historical magazine scan (domain mismatch). Replaced with PrimaLayout.

**Weight source note:** LayoutParser's built-in `lp://` model catalog points at Dropbox
links hosted by the original project maintainer; all of these have since been deleted
(Dropbox returns an HTTP 200 "File Deleted" page instead of a 404, which silently breaks
LayoutParser's config parsing). Weights for all three models tried were instead downloaded
from a community-maintained Hugging Face mirror (`huggingface.co/Eterna2/LayoutParser`) and
are loaded from local disk in `models/`.

## Specifications used

- Environment: conda env `layoutparser-env`, Python 3.11, Detectron2 (CPU build,
  `cpu_py311*` conda-forge package — no CUDA on this Apple Silicon Mac), LayoutParser,
  OpenCV, Pillow, PyMuPDF.
- Page rasterization: PDF pages rendered to PNG at **300 DPI**.

### Venv setup

Built from `venv_build_test/environment-layoutparser.yml`:

```yaml
name: layoutparser-env
channels:
  - conda-forge
dependencies:
  - python=3.11
  - detectron2=0.6=cpu_py311*
  - pip
  - pip:
      - layoutparser
      - pillow
      - opencv-python
      - pymupdf
```

To build and activate:

```
conda env create -f venv_build_test/environment-layoutparser.yml
conda activate layoutparser-env
```

The env directory is managed by conda (outside the repo, under `~/anaconda3/envs/`),
not committed to git — rebuild it from the yml file above on a fresh machine.
- Score threshold: **0.7** for the main batch run (chosen after comparing 0.5 / 0.7 / 0.75
  by eye against a test page — 0.7 cleanly dropped low-confidence margin noise while
  keeping all real text/image regions). A separate **0.5** threshold experiment was also
  run on 3 selected pages for comparison.

## Files created

- `venv_build_test/environment-layoutparser.yml` — conda environment spec.
- `venv_build_test/pdf_to_images.py` — rasterizes a PDF to per-page 300 DPI PNGs; accepts
  an optional `stem` override for naming.
- `venv_build_test/check_layoutparser_setup.py` — loads the PrimaLayout model, runs
  detection on one image, draws annotated boxes+labels, and prints results. Also defines
  the reusable `load_primalayout_model` / `print_layout` / `save_annotated_image` helpers
  that the batch pipeline imports.
- `models/PrimaLayout/{config.yml, model_final.pth}` — locally cached model weights/config
  (also `models/NewspaperNavigator/` and `models/PubLayNet/`, downloaded during evaluation
  but not used by the current pipeline).
- `pipeline/run_prima_batch.py` — batch driver: for each magazine PDF, rasterizes every
  page and runs PrimaLayout detection at threshold 0.7, writing results per page.
- `pipeline/additional_experiment_prima_run.py` — reruns PrimaLayout at threshold 0.5 on
  3 hand-picked pages (one per magazine) for side-by-side comparison against the 0.7 run.
- `.gitignore` — excludes `models/` (large binaries) and `build_texts/images/` (generated).

## What was run

1. Single-page sanity check on `build_texts/penny_1page_test.pdf` to validate the
   environment and compare candidate models/thresholds.
2. Full batch run (`pipeline/run_prima_batch.py`, threshold 0.7) across all three
   magazines' full sampled issues:
   - `penny` — 26 pages
   - `chambers` — 24 pages
   - `saturday` — 24 pages
3. Experimental low-threshold run (`pipeline/additional_experiment_prima_run.py`,
   threshold 0.5) on 3 specific pages: `chambers_page_014`, `penny_page_026`,
   `saturday_page_021`.

## Output

- `build_texts/images/<mag>_images/<mag>_page_NNN.png` — rasterized 300 DPI page images.
- `output/output_images_json_establishing_layout_AIs/<mag>_prima/<mag>_page_NNN_primalayout.png` — page image with detected boxes
  and `type + confidence score` labels drawn on it.
- `output/output_images_json_establishing_layout_AIs/<mag>_prima/json_bounding_<mag>_prima/<mag>_page_NNN_primalayout.json` — raw
  detections per page (`type`, `score`, `bbox`).
- `output/output_images_json_establishing_layout_AIs/<mag>_prima_experimental/` and its `json_bounding_<mag>_prima_experimental/`
  subfolder — same PNG/JSON outputs, but for the 3-page, 0.5-threshold experiment.
- `build_texts/images/one_page_load_tests/` — original single-page sanity-check artifacts,
  kept separate from the real multi-page magazine issues.
