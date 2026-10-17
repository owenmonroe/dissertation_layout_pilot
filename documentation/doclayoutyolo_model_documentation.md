# DocLayout-YOLO Pilot — Model Documentation

## Model used

**DocLayout-YOLO (DocStructBench checkpoint)** — a YOLOv10-based real-time layout
detection model, used **zero-shot** (no fine-tuning on our magazine scans). Weights:
`doclayout_yolo_docstructbench_imgsz1024.pt`, pulled from the Hugging Face repo
`juliozhao/DocLayout-YOLO-DocStructBench`.

Detected classes: `title`, `plain_text`, `abandon` (headers/footers/page numbers/
marginal notes), `figure`, `figure_caption`, `table`, `table_caption`,
`table_footnote`, `isolate_formula`, `formula_caption`.

Compared to PrimaLayout's 6 coarser classes, DocLayout-YOLO's taxonomy is more
granular — notably it separates `title` from body text, and has a dedicated
`abandon` class that PrimaLayout has no equivalent for (page furniture like
"Digitized by Google" / library attribution lines fall into it cleanly).

## Specifications used

- Inference device: **MPS** (Apple Silicon GPU via PyTorch's Metal backend),
  falls back to CPU if MPS isn't available (`torch.backends.mps.is_available()`).
- Page rasterization: PDF pages rendered to PNG at **300 DPI** (same rasters
  PrimaLayout uses, written independently by this pipeline's own PDF→PNG step).
- Inference image size: **1024px** (`imgsz=1024`, the size the DocStructBench
  checkpoint was trained/released at).
- Confidence threshold: **0.2** — chosen after eyeballing a single test page;
  even at 0.2 there was very little junk, everything above ~0.3 was a real,
  correctly-typed region, so no need to raise it like we did with PrimaLayout.

### Venv setup

Plain Python venv (not conda — DocLayout-YOLO is pure PyTorch/pip wheels, no
compiled extensions like Detectron2, so no need for conda-forge binaries):

```
/opt/homebrew/bin/python3.10 -m venv venv_build_test/doclayoutyolo-env
source venv_build_test/doclayoutyolo-env/bin/activate
pip install torch torchvision
pip install doclayout-yolo huggingface_hub pillow opencv-python
```

Note: `torch`/`torchvision` are installed from plain PyPI, **not** with
`--index-url https://download.pytorch.org/whl/cpu` — that index only hosts
Linux/Windows CPU-only builds. macOS wheels (which include MPS/Metal GPU
support) only live on the default PyPI index.

The venv directory itself is git-ignored (`venv_build_test/*-env/` in
`.gitignore`) — rebuild it from the commands above on a fresh machine, don't
expect it to be present after a fresh clone.

## Files created

- `venv_build_test/doclayoutyolo-env/` — the venv (git-ignored).
- `venv_build_test/check_doclayoutyolo_setup.py` — loads the DocLayout-YOLO
  model (downloading weights to `models/DocLayoutYOLO/` on first run), runs
  detection on one image, draws annotated boxes+labels, and prints results.
  Also defines the reusable `load_doclayoutyolo_model` / `_select_device` /
  `print_layout` / `save_annotated_image` helpers that the batch pipeline
  imports.
- `models/DocLayoutYOLO/doclayout_yolo_docstructbench_imgsz1024.pt` — locally
  cached model weights (git-ignored, re-downloadable from Hugging Face).
- `pipeline/run_doclayoutyolo_batch.py` — batch driver: for each magazine PDF,
  rasterizes every page (independently of the PrimaLayout pipeline — this
  script has no dependency on `layoutparser`/`run_prima_batch.py`, since it
  runs in a separate venv with a separate dependency stack) and runs
  DocLayout-YOLO detection at confidence threshold 0.2, writing results per
  page.

## What was run

1. Single-page sanity check (`check_doclayoutyolo_setup.py`) on
   `build_texts/images/one_page_load_tests/penny_1page_test_page001.png` to
   validate the environment and eyeball the confidence threshold.
2. Full batch run (`pipeline/run_doclayoutyolo_batch.py`, confidence 0.2)
   across all three magazines' full sampled issues:
   - `penny` — 26 pages
   - `chambers` — 24 pages
   - `saturday` — 24 pages

## Output

- `build_texts/images/<mag>_images/<mag>_page_NNN.png` — rasterized 300 DPI
  page images (shared with the PrimaLayout pipeline's output of the same
  name/location).
- `output/<mag>_yolo/<mag>_page_NNN_doclayoutyolo.png` — page image with
  detected boxes and `type + confidence score` labels drawn on it.
- `output/<mag>_yolo/json_bounding_<mag>_yolo/<mag>_page_NNN_doclayoutyolo.json`
  — raw detections per page (`type`, `score`, `bbox`).
