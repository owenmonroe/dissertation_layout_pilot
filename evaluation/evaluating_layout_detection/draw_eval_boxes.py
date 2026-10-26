"""Add readable box-index tags to the PrimaLayout / DocLayout-YOLO eval images.

Starts from each model's own annotated output image in output/output_images_json_establishing_layout_AIs/<mag>_<model>/
(boxes, colours and type labels exactly as the pipeline drew them) and only
adds a larger "#N" index tag per box on top. Nothing about the boxes changes.

Why: the pipeline's own "#N" labels were hard to read in two cases:
  - a box touching the top of the page had its label drawn off-image, and
  - boxes the model emitted twice with identical coordinates (YOLO does this
    when it predicts two classes for one region) had labels stacked on top
    of each other.
Here, boxes with (near-)identical coordinates share one tag ("#7 | #12"), tags are
kept on the page, and overlapping tags are nudged apart. Index numbers are
the position in the JSON "regions" list, same as before.

YOLO pages: the pipeline's small magenta "#N" labels are removed first, so
each box carries only the white tag. Only the magenta (255, 0, 255) label
pixels and their anti-aliased edges are replaced; every other pixel (boxes,
colours, YOLO's type/score labels) stays exactly as the pipeline output it. See strip_yolo_index_labels.
That step needs doclayout_yolo, so it runs in the DocLayout-YOLO venv as a
subprocess; the tags themselves are drawn by this (system) Python so they
render exactly as before.

Usage: python evaluation/evaluating_layout_detection/draw_eval_boxes.py
Writes evaluation/evaluating_layout_detection/boxing_output_for_eval/<mag>_{prima,yolo}_eval/*_eval.png
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parents[2]  # evaluation/<stage>/this file
EVAL_ROOT = Path(__file__).resolve().parent / "boxing_output_for_eval"
YOLO_PYTHON = REPO_ROOT / "venv_build_test" / "doclayoutyolo-env" / "bin" / "python"
MAGAZINES = ["chambers", "penny", "saturday"]
PAGES = ["001", "002", "003"]
MODELS = {
    # model key: (output folder suffix, json/png file suffix)
    "prima": ("prima", "primalayout"),
    "yolo": ("yolo", "doclayoutyolo"),
}
FONT_SIZE = 40
# Boxes whose corners are all within this many pixels share one tag.
SAME_BOX_TOLERANCE = 10
# DocLayout-YOLO DocStructBench class ids (model.names), for rebuilding its plot.
YOLO_CLASS_NAMES = {
    0: "title", 1: "plain text", 2: "abandon", 3: "figure", 4: "figure_caption",
    5: "table", 6: "table_caption", 7: "table_footnote", 8: "isolate_formula",
    9: "formula_caption",
}


def load_font() -> ImageFont.ImageFont:
    for name in ("Arial Bold.ttf", "Arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(size=FONT_SIZE)


def strip_yolo_index_labels(json_path: Path, src_png: Path, out_png: Path) -> None:
    """Return the YOLO pipeline image with its magenta "#N" labels removed.

    The pipeline draws result.plot() and then cv2.putText("#N") in pure
    magenta, which result.plot() itself never produces, so the pure-magenta
    pixels locate the index labels. Those pixels and their edges are
    filled from result.plot() rebuilt from the JSON, i.e. what was underneath
    them. The rebuilt plot isn't used for anything else: the JSON bboxes are
    rounded to 0.1 px, so its box edges can sit a pixel off the original.
    """
    import cv2
    import numpy as np
    import torch
    from doclayout_yolo.engine.results import Results

    page = json.loads(json_path.read_text())
    class_ids = {name: i for i, name in YOLO_CLASS_NAMES.items()}
    rows = [r["bbox"] + [r["score"], class_ids[r["type"]]] for r in page["regions"]]
    rebuilt = Results(
        cv2.imread(page["page_image"]),
        path=page["page_image"],
        names=YOLO_CLASS_NAMES,
        boxes=torch.tensor(rows) if rows else torch.zeros((0, 6)),
    ).plot(pil=True, line_width=5, font_size=20)  # same args as the pipeline

    original = cv2.imread(str(src_png))
    # The label text has anti-aliased edges blended with what's underneath, so
    # take a 2 px border around the pure-magenta core too, but only pixels that
    # actually differ from the rebuilt plot.
    core = np.all(original == (255, 0, 255), axis=2).astype(np.uint8)
    near_label = cv2.dilate(core, np.ones((3, 3), np.uint8), iterations=2).astype(bool)
    labels = near_label & np.any(original != rebuilt, axis=2)
    original[labels] = rebuilt[labels]
    cv2.imwrite(str(out_png), original)


def tag_page(json_path: Path, src_png: Path, out_path: Path, font, strip_labels=False) -> None:
    regions = json.loads(json_path.read_text())["regions"]
    if strip_labels:
        with tempfile.TemporaryDirectory() as tmp:
            stripped = Path(tmp) / "stripped.png"
            subprocess.run(
                [str(YOLO_PYTHON), __file__, "--strip-yolo-labels",
                 str(json_path), str(src_png), str(stripped)],
                check=True,
            )
            image = Image.open(stripped).convert("RGB")
    else:
        image = Image.open(src_png).convert("RGB")
    draw = ImageDraw.Draw(image)
    width, height = image.size

    # Group regions sharing (near enough) the same box so their indexes go on
    # one tag; otherwise the second tag gets nudged onto a neighbouring box.
    groups: dict[tuple, list[int]] = {}
    for i, region in enumerate(regions):
        bbox = tuple(region["bbox"])
        for key in groups:
            if all(abs(a - b) <= SAME_BOX_TOLERANCE for a, b in zip(key, bbox)):
                groups[key].append(i)
                break
        else:
            groups[bbox] = [i]

    placed: list[tuple] = []
    for (x1, y1, _x2, _y2), indexes in groups.items():
        label = " | ".join(f"#{i}" for i in indexes)
        # Sit the tag just inside the box's top-left corner, on the page.
        tx = min(max(x1 + 8, 0), width)
        ty = min(max(y1 + 8, 0), height)
        l, t, r, b = draw.textbbox((tx, ty), label, font=font)
        if r > width:
            shift = r - width + 6
            tx, l, r = tx - shift, l - shift, r - shift
        # Nudge down past any tag already placed where this one would go.
        moved = True
        while moved:
            moved = False
            for pl, pt, pr, pb in placed:
                if l < pr and r > pl and t < pb and b > pt:
                    dy = pb - t + 2
                    ty, t, b = ty + dy, t + dy, b + dy
                    moved = True
        box = (l - 5, t - 5, r + 5, b + 5)
        draw.rectangle(box, fill=(255, 255, 255), outline=(0, 0, 0), width=3)
        draw.text((tx, ty), label, fill=(0, 0, 0), font=font)
        placed.append(box)

    image.save(out_path)
    dupes = [g for g in groups.values() if len(g) > 1]
    note = f" (shared boxes: {dupes})" if dupes else ""
    print(f"  -> wrote {out_path.relative_to(REPO_ROOT)}{note}")


def main() -> None:
    font = load_font()
    for mag in MAGAZINES:
        for model, (folder, suffix) in MODELS.items():
            model_dir = REPO_ROOT / "output" / "output_images_json_establishing_layout_AIs" / f"{mag}_{folder}"
            json_dir = model_dir / f"json_bounding_{mag}_{folder}"
            out_dir = EVAL_ROOT / f"{mag}_{folder}_eval"
            for page in PAGES:
                base = f"{mag}_page_{page}_{suffix}"
                tag_page(
                    json_dir / f"{base}.json",
                    model_dir / f"{base}.png",
                    out_dir / f"{base}_eval.png",
                    font,
                    strip_labels=(model == "yolo"),
                )


if __name__ == "__main__":
    if sys.argv[1:2] == ["--strip-yolo-labels"]:
        # Called by tag_page, inside the DocLayout-YOLO venv.
        strip_yolo_index_labels(*map(Path, sys.argv[2:5]))
    else:
        main()
