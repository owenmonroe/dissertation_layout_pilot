"""
Batch pipeline: PDF -> 300 DPI page PNGs -> Google Document AI OCR -> results.

For each volume (magazine_rules_config.VOLUMES: a magazine PDF and its issue
pages), rasterizes those pages into <pdf folder>/images/<volume>_images/ (same rasters the PrimaLayout/DocLayout-YOLO
pipelines use) and calls the Document AI "google-parser-OCR" Document OCR
processor on each page image, same as the one-page check_docai_setup.py
check. For every page, writes into output/<volume>_google/:

  - <volume>_page_NNN_docai.png
      (page image with boxes drawn on it)
  - json_bounding_<volume>_google/<volume>_page_NNN_docai.json
      (full raw Document AI response for that page)

Cost note: Document OCR is free for the first 1,000 pages/month on this
processor, then $1.50/1,000 pages -- running this full ~75-page batch costs
$0.00 (see documentation/ for the pricing breakdown).

Run from the repo root, with the docai-env venv active:

    python pipeline/run_docai_batch.py
    python pipeline/run_docai_batch.py --volumes penny_1836 saturday_1840
"""

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "venv_build_test"))

from pdf_to_images import pdf_to_images  # noqa: E402
from check_docai_setup import (  # noqa: E402
    print_layout,
    process_document,
    save_annotated_image,
    save_raw_response,
)

sys.path.insert(0, str(REPO_ROOT / "pipeline" / "yolo_output_article_extraction"))
from magazine_rules_config import VOLUMES, page_range  # noqa: E402


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
    parser.add_argument("--force", action="store_true",
                        help="redo pages whose output already exists")
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    for magazine in args.volumes:
        volume = VOLUMES[magazine]
        pdf_path = REPO_ROOT / volume.pdf
        raster_dir = REPO_ROOT / volume.images_dir
        out_dir = REPO_ROOT / "output" / f"{magazine}_google"
        json_dir = out_dir / f"json_bounding_{magazine}_google"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {magazine}: {pdf_path.name} ===")
        pages = page_range(volume.pages)
        page_images = pdf_to_images(pdf_path, raster_dir, dpi=args.dpi, stem=magazine, pages=pages)
        print(f"Rasterized {len(page_images)} page(s) into {raster_dir}")

        for page_image_path in page_images:
            # PDF page number, from the image name (<volume>_page_NNN.png)
            page_index = int(page_image_path.stem.rsplit("_", 1)[1])
            done = json_dir / f"{magazine}_page_{page_index:03d}_{'docai'}.json"
            if done.exists() and not args.force:
                print(f"{page_image_path.name}: already done, skipped")
                continue
            print(f"\n{page_image_path.name}:")
            document = process_document(page_image_path)
            print_layout("  Document AI Document OCR", document)

            base = f"{magazine}_page_{page_index:03d}"
            save_annotated_image(page_image_path, document, out_dir / f"{base}_docai.png")

            json_path = json_dir / f"{base}_docai.json"
            save_raw_response(document, json_path)

    print("\nDone.")


if __name__ == "__main__":
    main()
