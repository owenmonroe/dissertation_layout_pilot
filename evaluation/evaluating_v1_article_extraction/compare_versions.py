"""Re-check a new pipeline version against an annotated reading-order log.

The log (evaluation/evaluating_v1_article_extraction/reading_order_error_log.csv) annotates the v1 output box by
box. This script looks up each logged box in the new version's output and
says what happened to it, so the log's v1 numbers become the "before" for
the new version (roadmap step 3). Boxes keep their region_id across versions
(YOLO's boxes don't change); boxes the new version adds (a box split at a
printed rule) aren't in the log.

Outcome per row:
  - errors, checked mechanically:
      merge         fixed if the box now starts an article (the log marks the
                    box where the missed item begins);
      split         fixed if the box no longer starts an article;
      misplacement  fixed if the strip box is gone (its words rejoined);
  - errors needing a look (role, misattached, missed, ...):
      missed        fixed if the words quoted in the note ('4585 tons.') are
                    now in a box on that page;
      changed       something about the box changed (its role, front/back
                    text cut from it, its article's start, title or series):
                    likely fixed, confirm by eye;
      unchanged     nothing changed: still an error;
  - rows logged ok:
      unchanged / renamed (only the role's name changed: byline ->
      front_matter, ...) / changed (boundary or role: a possible regression,
      review).

Writes one row per log row (--out) and the summary tables (<out>_summary.md),
and prints the summary.

    python evaluation/evaluating_v1_article_extraction/compare_versions.py --old v1 --new v2 \\
        --out evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v2.csv
"""

import argparse
import re
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]  # evaluation/<stage>/this file
EXTRACTION = REPO_ROOT / "output" / "article_extraction"
MAGAZINES = ["penny", "saturday", "chambers"]
# v1 role names replaced in v2 (decision 1) or labels that don't change the text's place.
RENAMED = {("byline", "front_matter"), ("title_note", "front_matter"),
           ("attribution", "back_matter"), ("end_note", "back_matter"), ("text", "table")}
START_ROLES = ["title", "series_heading", "text", "table", "figure"]


def load(version: str, mag: str):
    out = EXTRACTION / version / mag
    regions = pd.read_csv(out / f"{mag}_regions.csv")
    articles = pd.read_csv(out / f"{mag}_articles.csv").set_index("article_id")
    first = (regions[regions.article_id.notna() & regions.role.isin(START_ROLES)]
             .sort_values(["page", "reading_order"]).groupby("article_id").region_id.first())
    return regions.set_index("region_id"), articles, set(first)


def text(v) -> str:
    return "" if pd.isna(v) else str(v)


def outcome(row: dict) -> str:
    etype, verdict = row["error_type"], row["verdict"]
    if verdict == "excluded":
        return "excluded"
    if verdict == "ok":
        if row["old_start"] != row["new_start"] or (
                row["old_role"] != row["new_role"]
                and (row["old_role"], row["new_role"]) not in RENAMED):
            return "changed"
        return "renamed" if row["old_role"] != row["new_role"] else "unchanged"
    if etype == "merge":
        return "fixed" if row["new_start"] else "unchanged"
    if etype == "split":
        return "fixed" if not row["new_start"] else "unchanged"
    if etype == "missed":
        return "fixed" if row["missed_found"] else "unchanged"
    if etype == "misplacement":
        return "fixed" if not row["in_new"] or row["new_role"] not in ("text", "title") else "unchanged"
    changed = (not row["in_new"] or row["old_role"] != row["new_role"] or row["front_text"]
               or row["back_text"] or row["old_start"] != row["new_start"]
               or row["old_title"] != row["new_title"] or row["new_series"])
    return "changed" if changed else "unchanged"


def compare(old: str, new: str, log: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for mag in MAGAZINES:
        r_old, a_old, s_old = load(old, mag)
        r_new, a_new, s_new = load(new, mag)
        for _, entry in log[log.magazine == mag].iterrows():
            rid = entry.region_id
            in_new = rid in r_new.index
            o = r_old.loc[rid] if rid in r_old.index else None
            n = r_new.loc[rid] if in_new else None
            old_art = text(o.article_id) if o is not None else ""
            new_art = text(n.article_id) if n is not None else ""
            row = {
                "magazine": mag, "page": entry.page, "reading_order": entry.reading_order,
                "region_id": rid, "verdict": entry.verdict, "error_type": entry.error_type,
                "in_new": in_new,
                "old_role": text(o.role) if o is not None else "",
                "new_role": text(n.role) if n is not None else "",
                "old_start": rid in s_old, "new_start": rid in s_new,
                "old_title": text(a_old.title.get(old_art)) if old_art else "",
                "new_article_id": new_art,
                "new_title": text(a_new.title.get(new_art)) if new_art else "",
                "new_series": text(a_new.series.get(new_art)) if new_art else "",
                "front_text": text(n.front_text) if n is not None else "",
                "back_text": text(n.back_text) if n is not None else "",
                "notes": entry.notes,
            }
            quoted = re.findall(r"'([^']{3,60})'", entry.notes)
            page_text = " ".join(r_new[r_new.page == int(entry.page)].text.dropna())
            row["missed_found"] = bool(quoted) and quoted[0] in page_text
            row["outcome"] = outcome(row)
            rows.append(row)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--old", default="v1")
    parser.add_argument("--new", default="v2")
    parser.add_argument("--log", type=Path, default=Path(__file__).resolve().parent / "reading_order_error_log.csv")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()

    log = pd.read_csv(args.log, dtype=str, keep_default_na=False)
    df = compare(args.old, args.new, log)
    df.to_csv(args.out, index=False)

    summary = summarise(df, args.old, args.new)
    summary_path = args.out.with_name(args.out.stem + "_summary.md")
    summary_path.write_text(summary)
    print(summary)
    for path in (args.out, summary_path):
        print(f"Wrote {path.relative_to(REPO_ROOT) if path.is_relative_to(REPO_ROOT) else path}")


def summarise(df: pd.DataFrame, old: str, new: str) -> str:
    """The summary tables, as Markdown: every number here comes from the
    comparison, with no hand review."""
    errors = df[df.verdict == "error"].copy()
    errors["error_type"] = errors.error_type.str.split(";").str[0].str.strip()
    cols = [c for c in ["fixed", "changed", "unchanged"] if c in errors.outcome.unique()]
    by_type = pd.crosstab(errors.error_type, errors.outcome, margins=True, margins_name="total") \
        .reindex(columns=cols + ["total"], fill_value=0)
    by_mag = pd.crosstab(errors.magazine, errors.outcome, margins=True, margins_name="total") \
        .reindex(index=MAGAZINES + ["total"], columns=cols + ["total"], fill_value=0)
    ok = df[df.verdict == "ok"]
    changed_ok = ok[ok.outcome == "changed"]
    open_rows = errors[errors.outcome == "unchanged"]
    lines = [
        f"# {old} log re-checked against {new} output",
        "",
        "Written by `evaluation/evaluating_v1_article_extraction/compare_versions.py`. Outcomes: `fixed` (checked by the",
        "script: merge, split, misplacement, missed), `changed` (the box differs in",
        f"{new}, but whether it now matches the log needs annotation), `unchanged`",
        f"(the box is as in {old}: the error persists).",
        "",
        "## Logged errors by type", "", by_type.to_markdown(), "",
        "## Logged errors by magazine", "", by_mag.to_markdown(), "",
        f"## Rows logged ok ({len(ok)})", "",
        pd.Series(ok.outcome.value_counts()).to_frame("rows").to_markdown(), "",
    ]
    if len(changed_ok):
        lines += ["Logged-ok rows that changed (possible regressions):", "",
                  changed_ok[["magazine", "page", "reading_order", "old_role", "new_role",
                              "old_start", "new_start", "new_title"]].to_markdown(index=False), ""]
    lines += [f"## Errors unchanged in {new} ({len(open_rows)})", "",
              open_rows.assign(notes=open_rows.notes.str[:100])[
                  ["magazine", "page", "reading_order", "error_type", "notes"]].to_markdown(index=False), ""]
    return "\n".join(lines)

if __name__ == "__main__":
    main()
