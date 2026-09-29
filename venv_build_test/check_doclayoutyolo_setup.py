"""
Sanity-check script for the DocLayout-YOLO environment.

Run this after activating the venv:

    source venv_build_test/doclayoutyolo-env/bin/activate
    python venv_build_test/check_doclayoutyolo_setup.py path/to/a/sample_page.png

Uses the DocStructBench-finetuned DocLayout-YOLO checkpoint (YOLOv10-based,
zero-shot on our magazine scans -- no fine-tuning on our own data):
  -> finds: title, plain_text, abandon (headers/footers/page numbers),
            figure, figure_caption, table, table_caption, table_footnote,
            isolate_formula, formula_caption

Weights are pulled from the Hugging Face repo
juliozhao/DocLayout-YOLO-DocStructBench on first run and cached locally in
models/DocLayoutYOLO/ (explicit local file, same pattern as the PrimaLayout
weights in models/PrimaLayout/ -- not hidden away in the default
~/.cache/huggingface location).

This also saves an annotated copy of the input image with detected boxes
drawn on it, next to the input image, so you can visually inspect results
instead of just reading bbox coordinates off the terminal.
"""

import sys
from pathlib import Path

import cv2
import torch
from doclayout_yolo import YOLOv10
from huggingface_hub import hf_hub_download

_MODELS_DIR = Path(__file__).resolve().parent.parent / "models"

_HF_REPO_ID = "juliozhao/DocLayout-YOLO-DocStructBench"
_HF_FILENAME = "doclayout_yolo_docstructbench_imgsz1024.pt"


def _select_device() -> str:
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def load_doclayoutyolo_model() -> YOLOv10:
    local_dir = _MODELS_DIR / "DocLayoutYOLO"
    local_dir.mkdir(parents=True, exist_ok=True)
    weight_path = hf_hub_download(
        repo_id=_HF_REPO_ID,
        filename=_HF_FILENAME,
        local_dir=str(local_dir),
    )
    return YOLOv10(weight_path)


def print_layout(name: str, result, conf_thresh: float) -> None:
    boxes = result.boxes
    names = result.names
    print(f"{name} found {len(boxes)} region(s) at conf >= {conf_thresh}:")
    for box in boxes:
        cls_id = int(box.cls[0])
        score = float(box.conf[0])
        x1, y1, x2, y2 = [float(v) for v in box.xyxy[0]]
        print(
            f"  type={names[cls_id]!r:16s} score={score:.2f} "
            f"bbox=({x1:.0f}, {y1:.0f}, {x2:.0f}, {y2:.0f})"
        )


def save_annotated_image(result, out_path: Path) -> None:
    # result.plot() returns a BGR numpy array (despite the pil=True flag name
    # in some doclayout-yolo versions), so this is saved with cv2, not PIL.
    annotated = result.plot(pil=True, line_width=5, font_size=20)
    cv2.imwrite(str(out_path), annotated)
    print(f"  -> wrote {out_path}")


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python check_doclayoutyolo_setup.py path/to/page_image.png")
        sys.exit(1)

    image_path = Path(sys.argv[1])
    if not image_path.exists():
        print(f"Image not found: {image_path}")
        sys.exit(1)

    device = _select_device()
    print(f"Using device: {device}")

    print("\nLoading DocLayout-YOLO model (first run downloads weights, be patient)...")
    model = load_doclayoutyolo_model()

    conf_thresh = 0.2
    det_res = model.predict(
        str(image_path),
        imgsz=1024,
        conf=conf_thresh,
        device=device,
    )
    result = det_res[0]

    print_layout("DocLayout-YOLO", result, conf_thresh)
    save_annotated_image(
        result, image_path.with_name(image_path.stem + "_doclayoutyolo.png")
    )

    print("\nIf the section above printed a region list (even with 0 results), the environment works.")
    print("Zero results on a real page usually means the confidence threshold is too high,")
    print("not that the install is broken -- try lowering conf_thresh and rerun.")


if __name__ == "__main__":
    main()
