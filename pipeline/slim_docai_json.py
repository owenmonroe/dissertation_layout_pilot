"""Keep only what the pipeline uses from a Document AI response.

Document AI's full response embeds a copy of the page image (about 95% of the
file, 20-35 MB a page) and its own layout boxes (blocks, paragraphs), which
the pipeline doesn't use: it takes the words and lines, with coordinates, and
puts them into DocLayout-YOLO's boxes (text.py). The slim file keeps:

  - text: the full OCR text (word and line positions point into it);
  - pages[].pageNumber, dimension, detectedLanguages;
  - pages[].lines and pages[].tokens (words), each with coordinates
    (boundingPoly), its place in the text and the OCR confidence.

Everything dropped can be had again by re-running Document AI on the page.
run_docai_batch.py saves slim files; to slim existing ones:

    python pipeline/slim_docai_json.py <file.json> [...]
"""

import json
import sys
from pathlib import Path

PAGE_KEEP = ("pageNumber", "dimension", "detectedLanguages", "lines", "tokens")


def slim(doc: dict) -> dict:
    return {
        "text": doc.get("text", ""),
        "pages": [{k: page[k] for k in PAGE_KEEP if k in page} for page in doc.get("pages", [])],
        "slimmed": "page image, blocks and paragraphs removed (pipeline/slim_docai_json.py)",
    }


def slim_file(path: Path) -> tuple[int, int]:
    before = path.stat().st_size
    doc = json.loads(path.read_text())
    if "slimmed" not in doc:
        path.write_text(json.dumps(slim(doc)))
    return before, path.stat().st_size


if __name__ == "__main__":
    total_before = total_after = 0
    for name in sys.argv[1:]:
        before, after = slim_file(Path(name))
        total_before += before
        total_after += after
    print(f"{len(sys.argv) - 1} files: {total_before / 1e6:.0f} MB -> {total_after / 1e6:.0f} MB")
