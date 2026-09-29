"""
Batch pipeline: PDF -> 300 DPI page PNGs -> Google Document AI OCR -> results.

For each magazine PDF in test_texts/, rasterizes every page into
test_texts/images/<mag>_images/ (same rasters the PrimaLayout/DocLayout-YOLO
pipelines use) and calls the Document AI "google-parser-OCR" Document OCR
processor on each page image, same as the one-page check_docai_setup.py
check. For every page, writes into output/<mag>_google/:

  - <mag>_page_NNN_docai.png
      (page image with boxes drawn on it)
  - json_bounding_<mag>_google/<mag>_page_NNN_docai.json
      (full raw Document AI response for that page)

Cost note: Document OCR is free for the first 1,000 pages/month on this
processor, then $1.50/1,000 pages -- running this full ~75-page batch costs
$0.00 (see documentation/ for the pricing breakdown).

Run from the repo root, with the docai-env venv active:

    python pipeline/run_docai_batch.py
    python pipeline/run_docai_batch.py --magazines penny chambers
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

MAGAZINE_PDFS = {
    "penny": REPO_ROOT / "test_texts" / "penny_first3sample_inu-30000093220105-1779725606.pdf",
    "chambers": REPO_ROOT / "test_texts" / "chambers_first3sample_hvd-hwrgz7-1779381321.pdf",
    "saturday": REPO_ROOT / "test_texts" / "saturday_first3sample_osu-32435051594604-1779834449.pdf",
}
IMAGES_ROOT = REPO_ROOT / "test_texts" / "images"


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
    args = parser.parse_args()

    for magazine in args.magazines:
        pdf_path = MAGAZINE_PDFS[magazine]
        raster_dir = IMAGES_ROOT / f"{magazine}_images"
        out_dir = REPO_ROOT / "output" / f"{magazine}_google"
        json_dir = out_dir / f"json_bounding_{magazine}_google"
        out_dir.mkdir(parents=True, exist_ok=True)
        json_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n=== {magazine}: {pdf_path.name} ===")
        page_images = pdf_to_images(pdf_path, raster_dir, dpi=args.dpi, stem=magazine)
        print(f"Rasterized {len(page_images)} page(s) into {raster_dir}")

        for page_index, page_image_path in enumerate(page_images, start=1):
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
