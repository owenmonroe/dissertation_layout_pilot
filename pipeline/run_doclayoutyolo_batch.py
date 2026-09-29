"""
Batch pipeline: PDF -> 300 DPI page PNGs -> DocLayout-YOLO detection -> results.

For each magazine PDF in test_texts/, rasterizes every page into
test_texts/images/<mag>_images/ (same rasters the PrimaLayout pipeline uses --
shared, not duplicated, since both pipelines rasterize at the same 300 DPI)
and runs the DocLayout-YOLO DocStructBench model on each page image, same as
the one-page check_doclayoutyolo_setup.py check. For every page, writes into
output/<mag>_yolo/:

  - <mag>_page_NNN_doclayoutyolo.png
      (page image with boxes drawn on it)
  - json_bounding_<mag>_yolo/<mag>_page_NNN_doclayoutyolo.json
      (raw boxes: type, score, bbox)

Run from the repo root, with the doclayoutyolo-env venv active:

    python pipeline/run_doclayoutyolo_batch.py
    python pipeline/run_doclayoutyolo_batch.py --magazines penny chambers
    python pipeline/run_doclayoutyolo_batch.py --conf-thresh 0.2
"""

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "venv_build_test"))

from pdf_to_images import pdf_to_images  # noqa: E402
from check_doclayoutyolo_setup import (  # noqa: E402
    _select_device,
    load_doclayoutyolo_model,
    print_layout,
    save_annotated_image,
)

MAGAZINE_PDFS = {
    "penny": REPO_ROOT / "test_texts" / "penny_first3sample_inu-30000093220105-1779725606.pdf",
    "chambers": REPO_ROOT / "test_texts" / "chambers_first3sample_hvd-hwrgz7-1779381321.pdf",
    "saturday": REPO_ROOT / "test_texts" / "saturday_first3sample_osu-32435051594604-1779834449.pdf",
}
IMAGES_ROOT = REPO_ROOT / "test_texts" / "images"


def layout_to_json(result, page_image_path: Path) -> dict:
    boxes = result.boxes
    names = result.names
    return {
        "page_image": str(page_image_path),
        "regions": [
            {
                "type": names[int(box.cls[0])],
                "score": round(float(box.conf[0]), 4),
                "bbox": [round(float(v), 1) for v in box.xyxy[0]],
            }
            for box in boxes
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
    parser.add_argument("--conf-thresh", type=float, default=0.2)
    parser.add_argument("--imgsz", type=int, default=1024)
    args = parser.parse_args()

    device = _select_device()
    print(f"Using device: {device}")

    print("Loading DocLayout-YOLO model...")
    model = load_doclayoutyolo_model()

    for magazine in args.magazines:
        pdf_path = MAGAZINE_PDFS[magazine]
        raster_dir = IMAGES_ROOT / f"{magazine}_images"
        out_dir = REPO_ROOT / "output" / f"{magazine}_yolo"
        json_dir = out_dir / f"json_bounding_{magazine}_yolo"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {magazine}: {pdf_path.name} ===")
        page_images = pdf_to_images(pdf_path, raster_dir, dpi=args.dpi, stem=magazine)
        print(f"Rasterized {len(page_images)} page(s) into {raster_dir}")

        for page_index, page_image_path in enumerate(page_images, start=1):
            det_res = model.predict(
                str(page_image_path),
                imgsz=args.imgsz,
                conf=args.conf_thresh,
                device=device,
                verbose=False,
            )
            result = det_res[0]

            print(f"\n{page_image_path.name}:")
            print_layout("  DocLayout-YOLO", result, args.conf_thresh)

            base = f"{magazine}_page_{page_index:03d}"
            save_annotated_image(result, out_dir / f"{base}_doclayoutyolo.png")

            json_path = json_dir / f"{base}_doclayoutyolo.json"
            json_path.write_text(json.dumps(layout_to_json(result, page_image_path), indent=2))
            print(f"  -> wrote {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
