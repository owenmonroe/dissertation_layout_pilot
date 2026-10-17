"""Article extraction from DocLayout-YOLO output.

YOLO boxes -> roles, columns and reading order (layout.py) -> text per box
(text.py: Document AI OCR lines, or tesseract) -> articles (articles.py) ->
three linked tables, written as CSV and into one SQLite database:

  pages     one row per page: printed page number, issue number/date
  articles  one row per article: title, full text, pages it runs over
  regions   one row per YOLO box: role, column (left / right; middle for
            chambers), reading order, position, text, and the article it
            belongs to (figures included,
            with a crop saved to figures/)

Writes output/article_extraction/<version>/<mag>/ (CSVs, figures/,
reading_order/ check images, run_info.json) and
output/article_extraction/<version>/articles.sqlite (rows for this magazine
replaced on each run), where <version> is PIPELINE_VERSION below. Every table
row carries pipeline_version, and run_info.json records the git commit the
output came from. Frozen versions (v1: tag extraction-v1, the evaluated
output) are never written to.

Run from the repo root with any Python that has pandas and Pillow:

    python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny
    python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny --pages 1-3
    python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny --ocr tesseract
"""

import argparse
import datetime
import json
import sqlite3
import subprocess
import sys
import warnings
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

from articles import page_metadata, segment
from layout import REPO_ROOT, load_page, mark_masthead, order_regions
from magazine_rules_config import VOLUMES, magazine_rules, page_range
from duplicates import find_duplicates, set_aside
from rules import mark_rules
from volume_index import check_index, parse_index
from text import (assign_docai_text, assign_tesseract_text, clean_marks, docai_json_path,
                  drop_empty, recover_unboxed)

# The rules version this code implements; output goes to its own folder.
# v1 is frozen (git tag extraction-v1; output/article_extraction/v1/ is the
# output the reading-order evaluation describes). Bump this when a version is
# frozen and work on the next one starts.
PIPELINE_VERSION = "v2"
FROZEN_VERSIONS = {"v1"}
OUT_ROOT = REPO_ROOT / "output" / "article_extraction" / PIPELINE_VERSION
DB_PATH = OUT_ROOT / "articles.sqlite"
CHECK_IMAGE_SCALE = 0.4
PALETTE = ["#d62728", "#1f77b4", "#2ca02c", "#9467bd", "#ff7f0e", "#17becf",
           "#e377c2", "#8c564b", "#bcbd22", "#7f7f7f"]


def parse_pages(spec: str | None, magazine: str) -> list[int]:
    """Pages to extract: --pages, else the volume's issue pages, else every
    page with YOLO output."""
    pages = page_range(spec) or page_range(VOLUMES[magazine].pages)
    if pages:
        return pages
    json_dir = REPO_ROOT / "output" / f"{magazine}_yolo" / f"json_bounding_{magazine}_yolo"
    return sorted(int(p.name.split("_")[2]) for p in json_dir.glob("*.json"))


def column_name(column: int | None, magazine: str) -> str:
    """Column as a word: left / right (left / middle / right for 3 columns);
    "spanning" for a box across columns."""
    if column is None:
        return "spanning"
    return magazine_rules(magazine).column_names[column - 1]


def save_check_image(pg, article_of: dict, out_path: Path) -> None:
    """Page with content boxes coloured by article and labelled
    '<reading order> · <article>' (or the role, e.g. 'imprint', for a box in
    no article); masthead / furniture / dropped boxes in grey. Labels that
    would overlap are nudged down so none is hidden."""
    with Image.open(pg.image_path) as im:
        image = im.convert("RGB").resize(
            (int(pg.width * CHECK_IMAGE_SCALE), int(pg.height * CHECK_IMAGE_SCALE)))
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("Arial Bold.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    s = CHECK_IMAGE_SCALE
    labels = []
    for r in pg.regions:
        box = [v * s for v in r.bbox]
        if not r.order:
            draw.rectangle(box, outline="#999999", width=2)
            continue
        art = article_of.get(r.region_id)
        colour = PALETTE[(int(art.split("_")[-1]) - 1) % len(PALETTE)] if art else "#000000"
        draw.rectangle(box, outline=colour, width=4)
        labels.append((r.order, box, colour, f"{r.order} · {art.split('_')[-1].lstrip('0') if art else r.role}"))
    placed = []
    for _, box, colour, label in sorted(labels):  # in reading order
        x, y = box[0] + 4, box[1] + 4
        l, t, rr, b = draw.textbbox((x, y), label, font=font)
        moved = True
        while moved:
            moved = False
            for pl, pt, pr, pb in placed:
                if l < pr and rr > pl and t < pb and b > pt:
                    dy = pb - t + 4
                    y, t, b = y + dy, t + dy, b + dy
                    moved = True
        draw.rectangle((l - 3, t - 3, rr + 3, b + 3), fill=colour)
        draw.text((x, y), label, fill="white", font=font)
        placed.append((l - 3, t - 3, rr + 3, b + 3))
    image.save(out_path, quality=85)


def extract(mag: str, page_spec: str | None = None, ocr: str = "docai") -> dict:
    """Run the pipeline for one magazine in memory: returns the pages, the
    articles, the region -> article map, and the three tables. Writes nothing."""
    pages, page_rows = [], []
    for n in parse_pages(page_spec, mag):
        pg = load_page(mag, n)
        use_docai = ocr == "docai" and docai_json_path(mag, n).exists()
        unboxed = assign_docai_text(pg) if use_docai else assign_tesseract_text(pg)
        unboxed = recover_unboxed(pg, unboxed)
        clean_marks(pg)
        drop_empty(pg)
        mark_rules(pg)
        mark_masthead(pg)
        order_regions(pg)
        pages.append(pg)
        # Unboxed text joins the masthead text: masthead lines YOLO drew no box
        # for (e.g. the issue number) are found there.
        meta = page_metadata(pg, " | ".join(l.text for l in unboxed))
        masthead_text = " | ".join(r.text for r in pg.regions if r.role == "masthead" and r.text)
        page_rows.append({
            "magazine": mag, "page": n, **meta, "issue_start": pg.issue_start,
            "masthead_text": masthead_text or None,
            "ocr": "docai" if use_docai else "tesseract",
            "n_boxes": len(pg.regions),
            "n_content": sum(1 for r in pg.regions if r.order),
            "n_dropped": sum(1 for r in pg.regions if r.role == "dropped"),
            "n_recovered": sum(1 for r in pg.regions if r.yolo_type == "unboxed_ocr"),
            "unboxed_lines": len(unboxed),
            "unboxed_text": " | ".join(l.text for l in unboxed),
            "page_image": str(pg.image_path.relative_to(REPO_ROOT)),
        })

    duplicates = find_duplicates(pages)
    for pg in pages:
        if pg.page in duplicates:
            set_aside(pg, duplicates[pg.page])
    for row in page_rows:
        row["duplicate_of"] = duplicates.get(row["page"])
        if row["duplicate_of"]:
            row["issue_start"] = False
    articles = segment([pg for pg in pages if pg.page not in duplicates])
    # Segmenting can set boxes aside as furniture (no words, printer's
    # signatures, magazine name): renumber reading order without them.
    for pg in pages:
        for n, r in enumerate((r for r in pg.ordered if r.role != "furniture"), start=1):
            r.order = n
        for r in pg.regions:
            if r.role == "furniture":
                r.order = None
    index_rows = None
    volume = VOLUMES[mag]
    if volume.index_pdf or volume.index_pages:
        entries = parse_index(REPO_ROOT / (volume.index_pdf or volume.pdf),
                              page_range(volume.index_pages))
        index_rows = check_index(entries, articles, page_rows)
    pages_df = pd.DataFrame(page_rows)
    # Issue number / date for each issue, from its pages (masthead first).
    issue_seq, seq = [], 0
    for pg in pages:
        seq += pg.issue_start or seq == 0
        issue_seq.append(seq)
    pages_df["issue_seq"] = issue_seq
    # Per issue: the number from its masthead; the date from whichever page has
    # it with the year (issue-start pages often lose the year to OCR).
    by_issue = pages_df.sort_values(["issue_start"], ascending=False).groupby("issue_seq")
    issue_meta = by_issue[["issue_no", "issue_date"]].first()
    for seq, group in by_issue:
        with_year = [d for d in group["issue_date"].dropna() if d[-4:].isdigit()]
        if with_year:
            issue_meta.loc[seq, "issue_date"] = with_year[0]
    # A date OCR'd without its year takes the year of the issue before it.
    year = None
    for seq, date in issue_meta["issue_date"].items():
        if isinstance(date, str) and date[-4:].isdigit():
            year = date[-4:]
        elif isinstance(date, str) and year:
            issue_meta.loc[seq, "issue_date"] = f"{date}, {year}"

    issue_meta["issue_check"] = check_issue_numbers(issue_meta)
    pages_df["issue_check"] = pages_df["issue_seq"].map(issue_meta["issue_check"])
    # Every page carries its issue's number and full date.
    pages_df["issue_no"] = pages_df["issue_seq"].map(issue_meta["issue_no"])
    pages_df["issue_date"] = pages_df["issue_seq"].map(issue_meta["issue_date"])

    article_of = {}
    article_rows = []
    for a in articles:
        for r in a.all_regions:
            article_of[r.region_id] = a.article_id
        meta = issue_meta.loc[a.issue_seq] if a.issue_seq in issue_meta.index else {}
        cols = sorted({(r.page, r.column) for r in a.regions if r.column})
        article_rows.append({
            "article_id": a.article_id, "magazine": mag, "issue_seq": a.issue_seq,
            "issue_no": meta.get("issue_no"), "issue_date": meta.get("issue_date"),
            "title": a.title, "title_source": a.title_source, "article_type": a.article_type,
            "series": a.series or None, "series_part": a.series_part or None,
            "series_evidence": a.series_evidence or None,
            "continues_article_id": a.continues_article_id or None,
            "continued_by_article_id": a.continued_by_article_id or None,
            "continuation_evidence": a.continuation_evidence or None,
            "index_entries": " | ".join(a.index_entries) or None,
            "front_matter": a.front_matter or None, "back_matter": a.back_matter or None,
            "subsections": "; ".join(a.subsections) or None,
            "start_page": a.pages[0] if a.pages else None,
            "end_page": a.pages[-1] if a.pages else None,
            "pages": ";".join(map(str, a.pages)),
            "page_columns": ";".join(f"p{p} {column_name(c, mag)}" for p, c in cols),
            "n_regions": len(a.regions), "n_figures": len(a.figures),
            "word_count": len(a.text.split()), "text": a.text,
            "n_tables": len(a.tables), "table_text": a.table_text or None,
        })

    region_rows = []
    for pg in pages:
        for r in sorted(pg.regions, key=lambda r: (r.order is None, r.order or 0, r.index)):
            region_rows.append({
                "region_id": r.region_id, "magazine": mag, "page": r.page,
                "yolo_index": r.index, "yolo_type": r.yolo_type, "score": r.score,
                "role": r.role,
                "column": column_name(r.column, mag)
                if r.role in ("title", "series_heading", "text", "table", "figure", "caption",
                              "front_matter", "back_matter")
                and r.order else None,
                "band": r.band if r.order else None,
                "reading_order": r.order, "article_id": article_of.get(r.region_id),
                "x1": round(r.x1), "y1": round(r.y1), "x2": round(r.x2), "y2": round(r.y2),
                "y_top_frac": round(r.y1 / pg.height, 3), "y_bottom_frac": round(r.y2 / pg.height, 3),
                "text": r.text, "caption": r.caption or None,
                "front_text": r.front_text or None, "back_text": r.back_text or None,
                "image_file": str(figure_path(r).relative_to(REPO_ROOT)) if r.role == "figure" else None,
                "note": r.note or None,
            })

    tables = {
        "pages": pages_df,
        "articles": pd.DataFrame(article_rows),
        "regions": pd.DataFrame(region_rows),
    }
    if index_rows is not None:
        tables["index_check"] = pd.DataFrame(index_rows).assign(magazine=mag)
    # The publisher's imprint of each issue, for publishing history (who
    # published and printed it, where, at what price, over the years).
    seq_of = dict(zip(pages_df["page"], pages_df["issue_seq"]))
    imprint_rows = []
    for seq, meta in issue_meta.iterrows():
        boxes = sorted((r for pg in pages if seq_of[pg.page] == seq
                        for r in pg.regions if r.role == "imprint"),
                       key=lambda r: (r.page, r.y1, r.x1))
        imprint_rows.append({
            "magazine": mag, "issue_seq": seq, "issue_no": meta.get("issue_no"),
            "issue_date": meta.get("issue_date"),
            "pages": ";".join(sorted({str(r.page) for r in boxes})) or None,
            "n_boxes": len(boxes),
            "imprint_text": " | ".join(r.text.strip() for r in boxes if r.text.strip()) or None,
        })
    tables["imprints"] = pd.DataFrame(imprint_rows)
    for name, cols in {"pages": ["printed_page", "issue_no"], "articles": ["issue_no"],
                       "regions": ["band", "reading_order"]}.items():
        tables[name][cols] = tables[name][cols].astype("Int64")
    for df in tables.values():
        # magazine: which magazine's rules; volume: which run of pages (files, ids)
        df["magazine"] = volume.magazine
        df.insert(0, "volume", mag)
        df.insert(0, "pipeline_version", PIPELINE_VERSION)
    return {"pages": pages, "articles": articles, "article_of": article_of, "tables": tables}


# Digits OCR confuses with each other (Chambers "No. 3." read as "No. 8.").
CONFUSABLE = {frozenset(p) for p in ["38", "68", "08", "17", "56", "09"]}


def check_issue_numbers(issue_meta: pd.DataFrame) -> pd.Series:
    """Issue numbers should go up by one. Where the number read is one OCR-
    confusable digit away from the expected one, correct it (in place) and say
    so; otherwise flag gaps, restarts (a new series: read with the dates) and
    missing numbers. Returns the check text per issue ("" when in sequence)."""
    checks, prev = {}, None
    for seq in issue_meta.index:
        no = issue_meta.loc[seq, "issue_no"]
        expected = prev + 1 if prev is not None else None
        check = ""
        if pd.isna(no):
            check = "issue number not found" + (f" (expected {expected})" if expected else "")
        elif expected is not None and no != expected:
            read, want = str(int(no)), str(expected)
            diff = [(a, b) for a, b in zip(read, want) if a != b]
            if len(read) == len(want) and len(diff) == 1 and frozenset(diff[0]) in CONFUSABLE:
                issue_meta.loc[seq, "issue_no"] = expected
                check = f"corrected: read {read}, expected {want} (OCR confusion)"
            elif no < prev:
                check = f"restart: {prev} → {int(no)} (new series? check the dates)"
            else:
                check = f"gap: {prev} → {int(no)}"
        if not pd.isna(issue_meta.loc[seq, "issue_no"]):
            prev = int(issue_meta.loc[seq, "issue_no"])
        elif prev is not None:
            prev += 1  # carry the expected sequence past a missing number
        checks[seq] = check
    return pd.Series(checks)


def figure_path(r) -> Path:
    return OUT_ROOT / r.magazine / "figures" / f"{r.region_id}.jpg"


def git_state() -> tuple[str, bool]:
    """Current commit, and whether the pipeline code has uncommitted changes."""
    def git(*args):
        return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                              text=True).stdout.strip()
    code_dir = Path(__file__).resolve().parent.relative_to(REPO_ROOT)
    return git("rev-parse", "--short", "HEAD"), bool(git("status", "--porcelain", str(code_dir)))


def write_run_info(mag: str, result: dict, page_spec: str | None, ocr: str) -> None:
    commit, dirty = git_state()
    pages = [pg.page for pg in result["pages"]]
    info = {
        "pipeline_version": PIPELINE_VERSION,
        "git_commit": commit,
        "uncommitted_changes": dirty,
        "run_date": datetime.datetime.now().isoformat(timespec="seconds"),
        "volume": mag,
        "magazine": VOLUMES[mag].magazine,
        "split": VOLUMES[mag].split,
        "pdf": VOLUMES[mag].pdf,
        "pages": page_spec or f"{min(pages)}-{max(pages)}",
        "ocr": ocr,
    }
    (OUT_ROOT / mag / "run_info.json").write_text(json.dumps(info, indent=2) + "\n")


def write_outputs(mag: str, result: dict) -> None:
    """Figure crops, reading-order check images, CSVs, and this magazine's rows
    in the SQLite database."""
    out_dir = OUT_ROOT / mag
    for sub in ("figures", "reading_order"):
        (out_dir / sub).mkdir(parents=True, exist_ok=True)
    for pg in result["pages"]:
        for r in (r for r in pg.regions if r.role == "figure"):
            with Image.open(pg.image_path) as im:
                im.convert("RGB").crop(tuple(map(int, r.bbox))).save(figure_path(r), quality=90)
        save_check_image(pg, result["article_of"],
                         out_dir / "reading_order" / f"{mag}_page_{pg.page:03d}_order.jpg")
    with sqlite3.connect(DB_PATH) as db:
        for name, df in result["tables"].items():
            df.to_csv(out_dir / f"{mag}_{name}.csv", index=False)
            # Keep the other volumes' rows; rewrite the table so its columns
            # always match this version of the pipeline.
            exists = db.execute("select 1 from sqlite_master where type='table' and name=?",
                                (name,)).fetchone()
            others = pd.read_sql(f"select * from {name}", db) if exists else pd.DataFrame()
            if len(others):
                key = others["volume"] if "volume" in others else others["magazine"]
                others = others[key != mag]
            if len(others):
                with warnings.catch_warnings():  # all-empty columns (e.g. no bylines yet)
                    warnings.simplefilter("ignore", FutureWarning)
                    df = pd.concat([others, df], ignore_index=True)
            df.to_sql(name, db, if_exists="replace", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--volume", "--magazine", dest="volume", required=True, choices=sorted(VOLUMES),
                        help="volume key (magazine_rules_config.VOLUMES); the 1832 development "
                             "samples are penny / saturday / chambers")
    parser.add_argument("--pages", help="page range, e.g. 1-3 (default: the volume's issue pages, "
                                        "else every page with YOLO output)")
    parser.add_argument("--ocr", choices=["docai", "tesseract"], default="docai")
    args = parser.parse_args()

    if PIPELINE_VERSION in FROZEN_VERSIONS:
        sys.exit(f"{PIPELINE_VERSION} is frozen; its output must not be overwritten. "
                 "Set PIPELINE_VERSION to the version being built.")
    mag = args.volume
    result = extract(mag, args.pages, args.ocr)
    write_outputs(mag, result)
    write_run_info(mag, result, args.pages, args.ocr)
    articles = result["tables"]["articles"]
    n_figures = (result["tables"]["regions"]["role"] == "figure").sum()
    print(f"{mag}: {len(result['pages'])} pages, {len(articles)} articles, {n_figures} figures")
    for row in articles.itertuples():
        print(f"  {row.article_id}  p{row.pages:<8} {row.title_source:10} "
              f"{row.word_count:5} words  {row.title[:60]!r}")
    print(f"Wrote {(OUT_ROOT / mag).relative_to(REPO_ROOT)}/ and {DB_PATH.relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
