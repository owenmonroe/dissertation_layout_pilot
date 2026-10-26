"""
Batch pipeline: PDF -> 300 DPI page PNGs -> DocLayout-YOLO detection -> results.

For each volume (magazine_rules_config.VOLUMES: a magazine PDF and its issue
pages), rasterizes those pages into <pdf folder>/images/<volume>_images/ (same rasters the PrimaLayout pipeline uses --
shared, not duplicated, since both pipelines rasterize at the same 300 DPI)
and runs the DocLayout-YOLO DocStructBench model on each page image, same as
the one-page check_doclayoutyolo_setup.py check. For every page, writes into
output/output_images_json_*/<volume>_yolo/:

  - <volume>_page_NNN_doclayoutyolo.png  (only with --draw-boxes)
      (page image with boxes drawn on it)
  - json_bounding_<volume>_yolo/<volume>_page_NNN_doclayoutyolo.json
      (raw boxes: type, score, bbox)

Run from the repo root, with the doclayoutyolo-env venv active:

    python pipeline/run_doclayoutyolo_batch.py
    python pipeline/run_doclayoutyolo_batch.py --volumes penny_1836 saturday_1840
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

sys.path.insert(0, str(REPO_ROOT / "pipeline" / "yolo_output_article_extraction"))
from magazine_rules_config import VOLUMES, page_range  # noqa: E402


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
        "--volumes", "--magazines",
        dest="volumes",
        nargs="+",
        choices=sorted(VOLUMES),
        default=[k for k, v in VOLUMES.items() if v.split == "build"],
        help="Which volumes to process (magazine_rules_config.VOLUMES; default: the "
             "development samples). Only the volume's issue pages are processed.",
    )
    parser.add_argument("--draw-boxes", action="store_true",
                        help="also save the page with the model's boxes drawn on it (for comparing "
                             "models; extraction runs don't need it: their check images are in "
                             "output/article_extraction/<version>/<volume>/reading_order/)")
    parser.add_argument("--force", action="store_true",
                        help="redo pages whose output already exists")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--conf-thresh", type=float, default=0.2)
    parser.add_argument("--imgsz", type=int, default=1024)
    args = parser.parse_args()

    device = _select_device()
    print(f"Using device: {device}")

    print("Loading DocLayout-YOLO model...")
    model = load_doclayoutyolo_model()

    for magazine in args.volumes:
        volume = VOLUMES[magazine]
        pdf_path = REPO_ROOT / volume.pdf
        raster_dir = REPO_ROOT / volume.images_dir
        out_dir = REPO_ROOT / volume.model_output_dir / f"{magazine}_yolo"
        json_dir = out_dir / f"json_bounding_{magazine}_yolo"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {magazine}: {pdf_path.name} ===")
        pages = page_range(volume.pages)
        page_images = pdf_to_images(pdf_path, raster_dir, dpi=args.dpi, stem=magazine, pages=pages)
        print(f"Rasterized {len(page_images)} page(s) into {raster_dir}")

        for page_image_path in page_images:
            # PDF page number, from the image name (<volume>_page_NNN.png)
            page_index = int(page_image_path.stem.rsplit("_", 1)[1])
            done = json_dir / f"{magazine}_page_{page_index:03d}_{'doclayoutyolo'}.json"
            if done.exists() and not args.force:
                print(f"{page_image_path.name}: already done, skipped")
                continue
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
            if args.draw_boxes:
                save_annotated_image(result, out_dir / f"{base}_doclayoutyolo.png")

            json_path = json_dir / f"{base}_doclayoutyolo.json"
            json_path.write_text(json.dumps(layout_to_json(result, page_image_path), indent=2))
            print(f"  -> wrote {json_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
