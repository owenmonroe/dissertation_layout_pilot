"""Run a volume through the whole pipeline (roadmap step 4).

PDF -> 300 DPI page images -> DocLayout-YOLO -> Document AI OCR -> article
extraction, for any volume listed in
pipeline/yolo_output_article_extraction/magazine_rules_config.py (VOLUMES: its
magazine, PDF, issue pages and index pages). Each model step runs in its own
environment:

  - DocLayout-YOLO: venv_build_test/doclayoutyolo-env
  - Document AI:    venv_build_test/docai-env (Google credentials needed;
                    free for the first 1,000 pages a month, then $1.50 per 1,000)
  - extraction:     the Python running this script (pandas, Pillow, PyMuPDF)

Pages already rasterized, boxed or OCR'd are skipped, so a failed run can be
resumed without paying for OCR twice. Output: output/output_images_json_*/<volume>_yolo/,
output/output_images_json_*/<volume>_google/, output/article_extraction/<version>/<volume>/.

To add a volume: put its PDF in build_texts/ (rules are developed on it) or
evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/ (held out), add a Volume to VOLUMES, then:

    python pipeline/run_volume.py --volume penny_1836
    python pipeline/run_volume.py --volume penny_1836 --steps extract
"""

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "pipeline" / "yolo_output_article_extraction"))
from magazine_rules_config import VOLUMES  # noqa: E402

ENVS = REPO_ROOT / "venv_build_test"
STEPS = {
    "yolo": (ENVS / "doclayoutyolo-env" / "bin" / "python",
             REPO_ROOT / "pipeline" / "run_doclayoutyolo_batch.py", "--volumes"),
    "docai": (ENVS / "docai-env" / "bin" / "python",
              REPO_ROOT / "pipeline" / "run_docai_batch.py", "--volumes"),
    "extract": (Path(sys.executable),
                REPO_ROOT / "pipeline" / "yolo_output_article_extraction" / "run_extraction.py",
                "--volume"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--volume", required=True, choices=sorted(VOLUMES))
    parser.add_argument("--steps", nargs="+", choices=list(STEPS), default=list(STEPS),
                        help="steps to run, in order (default: all)")
    args = parser.parse_args()

    volume = VOLUMES[args.volume]
    if not (REPO_ROOT / volume.pdf).exists():
        sys.exit(f"PDF not found: {volume.pdf}")
    print(f"Volume {volume.key} ({volume.magazine}, {volume.split}): {volume.pdf}, "
          f"pages {volume.pages or 'all'}, index pages {volume.index_pages or '-'}")
    for step in args.steps:
        python, script, flag = STEPS[step]
        if not python.exists():
            sys.exit(f"{step}: environment not found ({python})")
        print(f"\n=== {step} ===", flush=True)
        done = subprocess.run([str(python), str(script), flag, volume.key], cwd=REPO_ROOT)
        if done.returncode:
            sys.exit(f"{step} failed (exit {done.returncode}); fix and re-run: finished pages are kept")
    print(f"\nDone: {volume.key}")


if __name__ == "__main__":
    main()
