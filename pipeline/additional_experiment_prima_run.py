"""
One-off experiment: rerun PrimaLayout at a lower score threshold (0.5 vs the
main pipeline's 0.7) on a single hand-picked page per magazine, to see what
extra/marginal detections show up below the main threshold.

Pages (chosen for comparison against their existing 0.7-threshold output in
output/<mag>_prima/):
  chambers page 014
  penny    page 026
  saturday page 021

Reuses the already-rasterized page images from
build_texts/images/<mag>_images/ (run pipeline/run_prima_batch.py first if
those don't exist yet). Writes into output/<mag>_prima_experimental/:

  - <mag>_page_NNN_primalayout.png
  - json_bounding_<mag>_prima_experimental/<mag>_page_NNN_primalayout.json

Run from the repo root, with the layoutparser-env conda env active:

    python pipeline/additional_experiment_prima_run.py
    python pipeline/additional_experiment_prima_run.py --score-thresh 0.4
"""

import argparse
import json
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "venv_build_test"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from check_layoutparser_setup import (  # noqa: E402
    load_primalayout_model,
    print_layout,
    save_annotated_image,
)
from run_prima_batch import layout_to_json  # noqa: E402

IMAGES_ROOT = REPO_ROOT / "build_texts" / "images"

# (magazine, page_number) pairs to run this experiment on.
EXPERIMENT_PAGES = [
    ("chambers", 14),
    ("penny", 26),
    ("saturday", 21),
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--score-thresh", type=float, default=0.5)
    args = parser.parse_args()

    print("Loading PrimaLayout model...")
    model = load_primalayout_model(score_thresh=args.score_thresh)

    for magazine, page_num in EXPERIMENT_PAGES:
        page_image_path = IMAGES_ROOT / f"{magazine}_images" / f"{magazine}_page_{page_num:03d}.png"
        if not page_image_path.exists():
            print(f"SKIP (raster not found, run run_prima_batch.py first): {page_image_path}")
            continue

        out_dir = REPO_ROOT / "output" / f"{magazine}_prima_experimental"
        json_dir = out_dir / f"json_bounding_{magazine}_prima_experimental"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        image = cv2.imread(str(page_image_path))
        if image is None:
            print(f"SKIP (unreadable): {page_image_path}")
            continue

        layout = model.detect(image)
        print(f"\n{page_image_path.name}:")
        print_layout("  PrimaLayout", layout)

        base = f"{magazine}_page_{page_num:03d}"
        save_annotated_image(image, layout, out_dir / f"{base}_primalayout.png")

        json_path = json_dir / f"{base}_primalayout.json"
        json_path.write_text(json.dumps(layout_to_json(layout, page_image_path), indent=2))
        print(f"  -> wrote {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
