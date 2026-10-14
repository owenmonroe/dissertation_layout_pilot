"""Build the reading-order / article-assignment error log template.

One row per box the article-extraction pipeline placed: every box in a page's
reading order (titles, text, figures, captions, bylines, attributions,
imprints, ...) plus masthead boxes (not in the reading order, but a box wrongly
taken as masthead loses article text). Furniture (headers, page numbers,
margins) and dropped duplicate boxes are left out.

Rows are pre-filled verdict "ok"; during the evaluation only errors are
changed. Each row matches a labelled box on the check image
output/article_extraction/<mag>/reading_order/<mag>_page_NNN_order.jpg
('<reading order> · <article>').

Reads output/article_extraction/<mag>/<mag>_{regions,articles,pages}.csv, so
run the pipeline first. Usage:

    python evaluation/make_reading_order_template.py
    python evaluation/make_reading_order_template.py --magazines penny --out evaluation/x.csv

Refuses to overwrite an existing log (it may hold annotations) unless --force.
"""

import argparse
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
EXTRACTION = REPO_ROOT / "output" / "article_extraction"
DEFAULT_OUT = REPO_ROOT / "evaluation" / "reading_order_error_log.csv"
SNIPPET_WORDS = 8


def snippet(text, end=False) -> str:
    words = str(text).split() if isinstance(text, str) else []
    if len(words) <= SNIPPET_WORDS:
        return " ".join(words)
    return ("… " + " ".join(words[-SNIPPET_WORDS:])) if end else (" ".join(words[:SNIPPET_WORDS]) + " …")


def article_label(row) -> str:
    if isinstance(row.title, str) and row.title:
        return row.title
    if isinstance(row.attribution, str) and row.attribution:
        return f"[untitled — {row.attribution}]"
    return "[untitled]"


def magazine_rows(mag: str) -> pd.DataFrame:
    regions = pd.read_csv(EXTRACTION / mag / f"{mag}_regions.csv")
    articles = pd.read_csv(EXTRACTION / mag / f"{mag}_articles.csv")
    pages = pd.read_csv(EXTRACTION / mag / f"{mag}_pages.csv")
    titles = {a.article_id: article_label(a) for a in articles.itertuples()}
    issues = articles.groupby("issue_seq")[["issue_no", "issue_date"]].first()

    boxes = regions[regions["reading_order"].notna() | (regions["role"] == "masthead")].copy()
    boxes = boxes.merge(pages[["page", "printed_page", "issue_seq"]], on="page", how="left")
    boxes["issue_no"] = boxes["issue_seq"].map(issues["issue_no"])
    boxes["issue_date"] = boxes["issue_seq"].map(issues["issue_date"])
    boxes["article"] = boxes["article_id"].str.split("_").str[-1].str.lstrip("0")
    boxes["article_title"] = boxes["article_id"].map(titles)
    boxes["box_start"] = boxes["text"].map(snippet)
    boxes["box_end"] = boxes["text"].map(lambda t: snippet(t, end=True))
    boxes["verdict"] = "ok"
    boxes["error_type"] = ""
    boxes["notes"] = ""
    # Masthead boxes first on their page (they sit above the reading order).
    boxes["_sort"] = boxes["reading_order"].fillna(0)
    boxes = boxes.sort_values(["page", "_sort", "y1"])
    return boxes[[
        "magazine", "page", "printed_page", "issue_no", "issue_date", "reading_order",
        "region_id", "yolo_index", "column", "role", "article", "article_id", "article_title",
        "box_start", "box_end", "verdict", "error_type", "notes",
    ]]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--magazines", nargs="+", default=["penny", "saturday", "chambers"])
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--force", action="store_true", help="overwrite an existing log")
    args = parser.parse_args()

    if args.out.exists() and not args.force:
        sys.exit(f"{args.out} exists (it may hold annotations); use --force to overwrite")
    log = pd.concat([magazine_rows(m) for m in args.magazines], ignore_index=True)
    for col in ("printed_page", "issue_no", "reading_order"):
        log[col] = log[col].astype("Int64")
    log.to_csv(args.out, index=False)
    print(f"Wrote {args.out.relative_to(REPO_ROOT)}: {len(log)} boxes")
    print(log.groupby("magazine").agg(pages=("page", "nunique"), boxes=("region_id", "size"))
          .reindex(args.magazines).to_string())


if __name__ == "__main__":
    main()
