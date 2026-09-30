"""
Sanity-check script for the Google Document AI environment.

Run this after activating the venv:

    source venv_build_test/docai-env/bin/activate
    python venv_build_test/check_docai_setup.py path/to/a/sample_page.pdf

Calls your GCP project's "google-parser-OCR" Document OCR processor directly
with a local file (no GCS bucket needed for single-page testing). Unlike
PrimaLayout / DocLayout-YOLO, this is a proprietary cloud-hosted model
(undisclosed architecture/training data) that costs per page and requires
network access + billing on the GCP project.

Auth: Application Default Credentials (`gcloud auth application-default
login`) -- no service account key file involved, nothing to keep out of git.

A "google-parser" Layout Parser processor was tried first and dropped: on a
two-column historical magazine page it classified the whole body-text region
as a single table_block, and only 39 of 71 total blocks (including ones
nested inside that table) ever got a populated bounding box -- the ones that
did were scattered single words/short phrases, not usable paragraph-level
boxes. Disabling enable_table_annotation had no effect (same table
classification, same 39/71 count), matching known open reports of
return_bounding_boxes not reliably populating on that processor. Document OCR
uses a much older, more standard schema (page -> block -> paragraph -> word,
each with its own reliably-populated boundingPoly) and gets full OCR text for
free as a bonus, so it's the one used here now.

This also saves an annotated copy of the page with detected block boxes
drawn on it, and dumps the full raw response to JSON, so you can inspect
results directly instead of trusting a parsed summary.
"""

import io
import sys
from pathlib import Path

import pymupdf
from google.api_core.client_options import ClientOptions
from google.cloud import documentai
from PIL import Image, ImageDraw

_PROJECT_ID = "925277685122"
_LOCATION = "us"
_PROCESSOR_ID = "bd2ba60b573ca6e5"

_MIME_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".pdf": "application/pdf",
}


def process_document(file_path: Path) -> documentai.Document:
    opts = ClientOptions(api_endpoint=f"{_LOCATION}-documentai.googleapis.com")
    client = documentai.DocumentProcessorServiceClient(client_options=opts)
    name = client.processor_path(_PROJECT_ID, _LOCATION, _PROCESSOR_ID)

    mime_type = _MIME_TYPES.get(file_path.suffix.lower())
    if mime_type is None:
        raise ValueError(f"Unsupported file type: {file_path.suffix}")

    raw_document = documentai.RawDocument(
        content=file_path.read_bytes(), mime_type=mime_type
    )
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    return result.document


def save_raw_response(document: documentai.Document, out_path: Path) -> None:
    out_path.write_text(documentai.Document.to_json(document))
    print(f"  -> wrote raw response {out_path}")


def get_text(document: documentai.Document, layout) -> str:
    segments = layout.text_anchor.text_segments
    if not segments:
        return ""
    parts = []
    for seg in segments:
        start = int(seg.start_index) if seg.start_index else 0
        end = int(seg.end_index)
        parts.append(document.text[start:end])
    return "".join(parts)


def block_bbox(layout) -> tuple | None:
    verts = layout.bounding_poly.normalized_vertices
    if not verts:
        return None
    xs = [v.x for v in verts]
    ys = [v.y for v in verts]
    return (min(xs), min(ys), max(xs), max(ys))


def print_layout(name: str, document: documentai.Document) -> None:
    total_blocks = sum(len(page.blocks) for page in document.pages)
    print(f"{name} found {total_blocks} block(s) across {len(document.pages)} page(s):")
    n_with_bbox = 0
    for page_index, page in enumerate(document.pages, start=1):
        for block in page.blocks:
            bbox = block_bbox(block.layout)
            if bbox is not None:
                n_with_bbox += 1
            text = get_text(document, block.layout).strip().replace("\n", " ")
            print(f"  page={page_index} bbox={bbox} text={text[:60]!r}")
    print(f"  ({n_with_bbox}/{total_blocks} blocks had a bounding box)")
    print(f"\nFull OCR text length: {len(document.text)} characters")


def _load_first_page_as_image(file_path: Path) -> Image.Image:
    if file_path.suffix.lower() != ".pdf":
        return Image.open(file_path).convert("RGB")
    with pymupdf.open(file_path) as doc:
        pix = doc[0].get_pixmap(matrix=pymupdf.Matrix(300 / 72, 300 / 72))
        return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def save_annotated_image(image_path: Path, document: documentai.Document, out_path: Path) -> None:
    image = _load_first_page_as_image(image_path)
    width, height = image.size
    draw = ImageDraw.Draw(image)

    n_drawn = 0
    # Only page 1 is drawn -- this script rasterizes a single page for the
    # annotation overlay, matching the one-page sanity-test scope.
    for i, block in enumerate(document.pages[0].blocks):
        bbox = block_bbox(block.layout)
        if bbox is None:
            continue
        x1, y1, x2, y2 = bbox
        draw.rectangle(
            [x1 * width, y1 * height, x2 * width, y2 * height], outline="red", width=5
        )
        # Index matches this block's position in pages[0].blocks in the JSON,
        # so a box spotted here can be looked up directly in the JSON output.
        label = f"#{i}"
        text_bbox = draw.textbbox((x1 * width, y1 * height), label)
        draw.rectangle(text_bbox, fill="yellow")
        draw.text((x1 * width, y1 * height), label, fill="red")
        n_drawn += 1

    image.save(out_path)
    print(f"  -> wrote {out_path} ({n_drawn} box(es) drawn)")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python check_docai_setup.py path/to/page.pdf")
        sys.exit(1)

    file_path = Path(sys.argv[1])
    if not file_path.exists():
        print(f"File not found: {file_path}")
        sys.exit(1)

    print(f"Calling Document AI processor {_PROCESSOR_ID} ({_LOCATION})...")
    document = process_document(file_path)

    print_layout("Document AI Document OCR", document)

    save_raw_response(document, file_path.with_name(file_path.stem + "_docai_raw.json"))
    save_annotated_image(
        file_path, document, file_path.with_name(file_path.stem + "_docai.png")
    )

    print(
        "\nIf the section above printed a block list (even with 0 results), the "
        "environment works. Check the raw JSON file to see the full response."
    )


if __name__ == "__main__":
    main()
