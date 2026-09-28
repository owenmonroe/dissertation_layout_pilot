"""
Sanity-check script for the LayoutParser + Detectron2 environment.

Run this after activating the conda env:

    conda activate layoutparser-env
    python check_layoutparser_setup.py path/to/a/sample_page.png

It loads TWO models, since Newspaper Navigator alone does not detect
plain body text:

  1. Newspaper Navigator (Detectron2, trained on historic U.S. newspapers)
     -> finds: Photograph, Illustration, Map, Comics/Cartoon,
               Editorial Cartoon, Headline, Advertisement
     -> does NOT find generic paragraph/body text

  2. PubLayNet (Detectron2, trained on modern scientific documents)
     -> finds: Text, Title, List, Table, Figure
     -> this is your stand-in for "body text block" detection until/unless
        you fine-tune something more historically appropriate

For your pilot you'll likely want boxes from both, tagged by which
model produced them, since neither alone covers everything you care
about (article text + headlines/illustrations/ads).
"""

import sys
from pathlib import Path

import cv2
import layoutparser as lp


def load_newspaper_navigator_model(score_thresh: float = 0.5) -> lp.Detectron2LayoutModel:
    return lp.Detectron2LayoutModel(
        config_path="lp://NewspaperNavigator/faster_rcnn_R_50_FPN_3x/config",
        label_map={
            0: "Photograph",
            1: "Illustration",
            2: "Map",
            3: "Comics/Cartoon",
            4: "Editorial Cartoon",
            5: "Headline",
            6: "Advertisement",
        },
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", score_thresh],
    )


def load_publaynet_model(score_thresh: float = 0.5) -> lp.Detectron2LayoutModel:
    return lp.Detectron2LayoutModel(
        config_path="lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config",
        label_map={0: "Text", 1: "Title", 2: "List", 3: "Table", 4: "Figure"},
        extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", score_thresh],
    )


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

    print("\nLoading Newspaper Navigator model (first run downloads weights, be patient)...")
    nn_model = load_newspaper_navigator_model()
    nn_layout = nn_model.detect(image)
    print(f"Newspaper Navigator found {len(nn_layout)} region(s):")
    for block in nn_layout:
        print(
            f"  type={block.type!r:20s} score={block.score:.2f} "
            f"bbox=({block.block.x_1:.0f}, {block.block.y_1:.0f}, "
            f"{block.block.x_2:.0f}, {block.block.y_2:.0f})"
        )

    print("\nLoading PubLayNet model (first run downloads weights, be patient)...")
    pln_model = load_publaynet_model()
    pln_layout = pln_model.detect(image)
    print(f"PubLayNet found {len(pln_layout)} region(s):")
    for block in pln_layout:
        print(
            f"  type={block.type!r:10s} score={block.score:.2f} "
            f"bbox=({block.block.x_1:.0f}, {block.block.y_1:.0f}, "
            f"{block.block.x_2:.0f}, {block.block.y_2:.0f})"
        )

    print("\nIf both sections printed region lists (even with 0 results), the environment works.")
    print("Zero results on a real page usually means the score threshold is too high,")
    print("not that the install is broken -- try lowering score_thresh to 0.3 and rerun.")


if __name__ == "__main__":
    main()
