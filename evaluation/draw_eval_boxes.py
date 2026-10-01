"""Add readable box-index tags to the PrimaLayout / DocLayout-YOLO eval images.

Starts from each model's own annotated output image in output/<mag>_<model>/
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

Usage: python evaluation/draw_eval_boxes.py
Writes evaluation/output_eval/<mag>_{prima,yolo}_eval/*_eval.png
"""

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

REPO_ROOT = Path(__file__).resolve().parent.parent
EVAL_ROOT = REPO_ROOT / "evaluation" / "output_eval"
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


def load_font() -> ImageFont.ImageFont:
    for name in ("Arial Bold.ttf", "Arial.ttf", "DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, FONT_SIZE)
        except OSError:
            continue
    return ImageFont.load_default(size=FONT_SIZE)


def tag_page(json_path: Path, src_png: Path, out_path: Path, font) -> None:
    regions = json.loads(json_path.read_text())["regions"]
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
            model_dir = REPO_ROOT / "output" / f"{mag}_{folder}"
            json_dir = model_dir / f"json_bounding_{mag}_{folder}"
            out_dir = EVAL_ROOT / f"{mag}_{folder}_eval"
            for page in PAGES:
                base = f"{mag}_page_{page}_{suffix}"
                tag_page(
                    json_dir / f"{base}.json",
                    model_dir / f"{base}.png",
                    out_dir / f"{base}_eval.png",
                    font,
                )


if __name__ == "__main__":
    main()
