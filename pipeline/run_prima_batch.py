"""
Batch pipeline: PDF -> 300 DPI page PNGs -> PrimaLayout detection -> results.

For each magazine PDF in build_texts/, rasterizes every page into
build_texts/images/<mag>_images/ and runs the PrimaLayout Detectron2 model on
each page image. For every page, writes into output/<mag>_prima/:

  - <mag>_page_NNN_primalayout.png
      (page image with boxes drawn on it)
  - json_bounding_<mag>_prima/<mag>_page_NNN_primalayout.json
      (raw boxes: type, score, bbox)

Run from the repo root, with the layoutparser-env conda env active:

    python pipeline/run_prima_batch.py
    python pipeline/run_prima_batch.py --magazines penny chambers
    python pipeline/run_prima_batch.py --score-thresh 0.7
"""

import argparse
import json
import sys
from pathlib import Path

import cv2

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "venv_build_test"))

from pdf_to_images import pdf_to_images  # noqa: E402
from check_layoutparser_setup import (  # noqa: E402
    load_primalayout_model,
    print_layout,
    save_annotated_image,
)

MAGAZINE_PDFS = {
    "penny": REPO_ROOT / "build_texts" / "penny_first3sample_inu-30000093220105-1779725606.pdf",
    "chambers": REPO_ROOT / "build_texts" / "chambers_first3sample_hvd-hwrgz7-1779381321.pdf",
    "saturday": REPO_ROOT / "build_texts" / "saturday_first3sample_osu-32435051594604-1779834449.pdf",
}

IMAGES_ROOT = REPO_ROOT / "build_texts" / "images"


def layout_to_json(layout, page_image_path: Path) -> dict:
    return {
        "page_image": str(page_image_path),
        "regions": [
            {
                "type": block.type,
                "score": round(float(block.score), 4),
                "bbox": [
                    round(float(block.block.x_1), 1),
                    round(float(block.block.y_1), 1),
                    round(float(block.block.x_2), 1),
                    round(float(block.block.y_2), 1),
                ],
            }
            for block in layout
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--magazines",
        nargs="+",
        choices=sorted(MAGAZINE_PDFS),
        default=sorted(MAGAZINE_PDFS),
        help="Which magazines to process (default: all).",
    )
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--score-thresh", type=float, default=0.7)
    args = parser.parse_args()

    print("Loading PrimaLayout model...")
    model = load_primalayout_model(score_thresh=args.score_thresh)

    for magazine in args.magazines:
        pdf_path = MAGAZINE_PDFS[magazine]
        raster_dir = IMAGES_ROOT / f"{magazine}_images"
        out_dir = REPO_ROOT / "output" / f"{magazine}_prima"
        json_dir = out_dir / f"json_bounding_{magazine}_prima"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {magazine}: {pdf_path.name} ===")
        page_images = pdf_to_images(pdf_path, raster_dir, dpi=args.dpi, stem=magazine)
        print(f"Rasterized {len(page_images)} page(s) into {raster_dir}")

        for page_index, page_image_path in enumerate(page_images, start=1):
            image = cv2.imread(str(page_image_path))
            if image is None:
                print(f"  SKIP (unreadable): {page_image_path}")
                continue

            layout = model.detect(image)
            print(f"\n{page_image_path.name}:")
            print_layout("  PrimaLayout", layout)

            base = f"{magazine}_page_{page_index:03d}"
            save_annotated_image(image, layout, out_dir / f"{base}_primalayout.png")

            json_path = json_dir / f"{base}_primalayout.json"
            json_path.write_text(json.dumps(layout_to_json(layout, page_image_path), indent=2))
            print(f"  -> wrote {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
