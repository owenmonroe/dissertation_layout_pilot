"""Regression check: do the pages already checked by hand still come out right?

verified_pages.json lists, for each checked page, the articles on it in
reading order (title, or "[untitled — <attribution>]"). This re-runs the
extraction in memory for each magazine (nothing is written) and reports any
page whose articles changed. Run it after changing a rule or magazines.py:

    python pipeline/yolo_output_article_extraction/check_verified.py

Exit code 0 if every page matches, 1 otherwise. To add a page once you have
checked it: python pipeline/yolo_output_article_extraction/check_verified.py
--add <magazine> <page> (records what the pipeline gives now; check it first).
"""

import argparse
import json
import sys
from pathlib import Path

from run_extraction import extract

VERIFIED = Path(__file__).with_name("verified_pages.json")


def article_label(row) -> str:
    if isinstance(row.title, str) and row.title:
        return row.title
    if isinstance(row.attribution, str) and row.attribution:
        return f"[untitled — {row.attribution}]"
    return "[untitled]"


def page_articles(tables: dict, page: int) -> list[str]:
    """Articles with title or text on the page, in reading order."""
    regions = tables["regions"]
    on_page = regions[(regions["page"] == page) & regions["role"].isin(["title", "text"])
                      & regions["article_id"].notna()].sort_values("reading_order")
    labels = {r.article_id: article_label(r) for r in tables["articles"].itertuples()}
    out = []
    for article_id in on_page["article_id"]:
        if not out or out[-1] != labels[article_id]:
            out.append(labels[article_id])
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--add", nargs=2, metavar=("MAGAZINE", "PAGE"),
                        help="record a newly checked page's current articles")
    parser.add_argument("--note", default="", help="with --add: who checked it / how")
    args = parser.parse_args()

    verified = json.loads(VERIFIED.read_text())
    if args.add:
        mag, page = args.add[0], int(args.add[1])
        tables = extract(mag)["tables"]
        entry = {"magazine": mag, "page": page, "checked": args.note,
                 "articles": page_articles(tables, page)}
        verified = [v for v in verified if (v["magazine"], v["page"]) != (mag, page)] + [entry]
        VERIFIED.write_text(json.dumps(verified, indent=2, ensure_ascii=False) + "\n")
        print(f"Recorded {mag} p{page}:", *entry["articles"], sep="\n  ")
        return

    failures = 0
    for mag in sorted({v["magazine"] for v in verified}):
        tables = extract(mag)["tables"]
        for v in (v for v in verified if v["magazine"] == mag):
            got = page_articles(tables, v["page"])
            if got == v["articles"]:
                print(f"ok    {mag} p{v['page']}  ({len(got)} articles)")
            else:
                failures += 1
                print(f"FAIL  {mag} p{v['page']}")
                print("      expected:", *v["articles"], sep="\n        ")
                print("      got:", *got, sep="\n        ")
    print(f"\n{len(verified) - failures}/{len(verified)} verified pages match")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
