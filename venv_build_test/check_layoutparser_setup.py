"""
Sanity-check script for the LayoutParser + Detectron2 environment.

Run this after activating the conda env:

    conda activate layoutparser-env
    python check_layoutparser_setup.py path/to/a/sample_page.png

Uses PrimaLayout (Detectron2, trained on historical European document scans
via the PRImA Layout Analysis dataset):
  -> finds: TextRegion, ImageRegion, TableRegion, MathsRegion,
            SeparatorRegion, OtherRegion

Newspaper Navigator (trained on historic U.S. newspapers, finds Photograph /
Illustration / Headline / Advertisement / etc.) was tried too, but on our
test page it only found the same illustration PrimaLayout already finds
(as an ImageRegion) and nothing else -- so it's dropped here as redundant.

This also saves an annotated copy of the input image with detected boxes
drawn on it, next to the input image, so you can visually inspect results
instead of just reading bbox coordinates off the terminal.
"""

import sys
from pathlib import Path

import cv2
import layoutparser as lp
from PIL import ImageDraw, ImageFont


# LayoutParser's built-in `lp://` model zoo points at Dropbox links that have
# since been deleted (returns an HTML "File Deleted" page instead of the real
# file), and its PathManager only recognizes a hardcoded set of URL prefixes
# (lp://, dropbox.com, one PaddleDetection host) so it can't auto-download
# from an arbitrary host either. Weights are downloaded ahead of time (see
# README / download commands) from a community mirror of the same files:
# https://huggingface.co/Eterna2/LayoutParser -- and loaded from local disk.
_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"


def load_primalayout_model(score_thresh: float = 0.7) -> lp.Detectron2LayoutModel:
    return lp.Detectron2LayoutModel(
        config_path=str(_MODELS_DIR / "PrimaLayout" / "config.yml"),
        model_path=str(_MODELS_DIR / "PrimaLayout" / "model_final.pth"),
        label_map={
            1: "TextRegion",
            2: "ImageRegion",
            3: "TableRegion",
            4: "MathsRegion",
            5: "SeparatorRegion",
            6: "OtherRegion",
        },
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", score_thresh],
    )


def print_layout(name: str, layout: lp.Layout) -> None:
    print(f"{name} found {len(layout)} region(s):")
    for block in layout:
        print(
            f"  type={block.type!r:14s} score={block.score:.2f} "
            f"bbox=({block.block.x_1:.0f}, {block.block.y_1:.0f}, "
            f"{block.block.x_2:.0f}, {block.block.y_2:.0f})"
        )


def save_annotated_image(image, layout: lp.Layout, out_path: Path) -> None:
    # lp.draw_box expects RGB; cv2 gives BGR.
    image_rgb = image[..., ::-1]
    # show_element_type=True is intentionally NOT used here: LayoutParser's
    # built-in label drawing calls the Pillow API font.getsize(), which was
    # removed in modern Pillow (Pillow 10+). Boxes are drawn plain here, then
    # labels are drawn manually below using the current Pillow API
    # (ImageDraw.textbbox) instead.
    annotated = lp.draw_box(image_rgb, layout, box_width=5, show_element_type=False)

    draw = ImageDraw.Draw(annotated)
    font = ImageFont.load_default()
    for block in layout:
        label = f"{block.type} {block.score:.2f}"
        x, y = block.block.x_1, block.block.y_1
        text_bbox = draw.textbbox((x, y), label, font=font)
        draw.rectangle(text_bbox, fill="yellow")
        draw.text((x, y), label, fill="black", font=font)

    annotated.save(out_path)
    print(f"  -> wrote {out_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python check_layoutparser_setup.py path/to/page_image.png")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        sys.exit(1)

    # LayoutParser/Detectron2 expects a BGR numpy array, which cv2.imread gives you.
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"OpenCV could not read image: {image_path}")
        sys.exit(1)

    print(f"Loaded image: {image_path}  shape={image.shape}")

    print("\nLoading PrimaLayout model (first run downloads weights, be patient)...")
    pl_model = load_primalayout_model()
    pl_layout = pl_model.detect(image)
    print_layout("PrimaLayout", pl_layout)
    save_annotated_image(
        image, pl_layout, image_path.with_name(image_path.stem + "_primalayout.png")
    )

    print("\nIf the section above printed a region list (even with 0 results), the environment works.")
    print("Zero results on a real page usually means the score threshold is too high,")
    print("not that the install is broken -- try lowering score_thresh and rerun.")


if __name__ == "__main__":
    main()
