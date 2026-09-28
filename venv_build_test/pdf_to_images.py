"""
Rasterize PDF pages to PNG images for LayoutParser/Detectron2, which
can only operate on images, not PDFs directly.

Usage:
    python pdf_to_images.py path/to/file.pdf [output_dir] [--dpi 300]

Writes one PNG per page: output_dir/<stem>_page_001.png, etc., where
<stem> defaults to the PDF's filename stem but can be overridden (e.g. to
a short magazine name instead of a long library-catalog filename).
Default output_dir is a sibling "images" folder next to the PDF.
"""

import argparse
from pathlib import Path

import pymupdf


def pdf_to_images(
    pdf_path: Path, output_dir: Path, dpi: int = 300, stem: str | None = None
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    zoom = dpi / 72  # PDF points are 72 per inch
    matrix = pymupdf.Matrix(zoom, zoom)
    name_stem = stem if stem is not None else pdf_path.stem

    written = []
    with pymupdf.open(pdf_path) as doc:
        for page_index, page in enumerate(doc, start=1):
            pix = page.get_pixmap(matrix=matrix)
            pix.set_dpi(dpi, dpi)
            out_path = output_dir / f"{name_stem}_page_{page_index:03d}.png"
            pix.save(out_path)
            written.append(out_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf_path", type=Path)
    parser.add_argument("output_dir", type=Path, nargs="?", default=None)
    parser.add_argument("--dpi", type=int, default=300)
    args = parser.parse_args()

    if not args.pdf_path.exists():
        raise SystemExit(f"PDF not found: {args.pdf_path}")

    output_dir = args.output_dir or (args.pdf_path.parent / "images")
    written = pdf_to_images(args.pdf_path, output_dir, dpi=args.dpi)

    print(f"Wrote {len(written)} page image(s) to {output_dir}:")
    for path in written:
        print(f"  {path}")


if __name__ == "__main__":
    main()
