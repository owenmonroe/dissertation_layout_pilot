"""Score a pipeline version's output against the gold article list.

The gold list (evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv) was annotated from the
printed test pages alone (documentation/article_extraction_pipeline_iterative_build/gold_article_list_annotation_guide.md).
Every gold item is located in the pipeline's output by its first and last
words (OCR-tolerant matching, limited to the gold item's pages), and
everything is decided mechanically:

  Item outcome (articles and editorial notices)
    exact     its first words open a pipeline article that holds no other gold
              item's start, and its last words are in the same article
    merged    its pipeline article also holds the start of the gold item
              before or after it (a missed boundary)
    split     its first and last words are in different pipeline articles
    lost      its first words are in no article's text: absorbed as front/back
              matter or a table, set aside (imprint, furniture), or not found

  Boundaries
    recall     gold items that open their own pipeline article / gold items
    precision  pipeline articles holding at least one gold item's start /
               pipeline articles (the rest are extra pieces)

  Fields, for each item that opens its own pipeline article (over all the
  pipeline articles it runs through, if it was split)
    title, front-matter and back-matter pieces (found in place / in the
    article text / missing; footnotes counted separately), series,
    continued-from, to-be-continued, editorial notice, illustrations (gold
    "fig:" notes vs. figures attached), issue number and date.

  Imprints: each issue's gold imprint, by its first and last words, in the
  pipeline's imprint for that issue.

Writes per-item, per-pipeline-article and per-imprint CSVs and a Markdown
summary. Used by evaluation/evaluating_v2_article_extraction/evaluate_v2_with_gold.ipynb; also runnable:

    python evaluation/evaluating_v2_article_extraction/score_gold.py --version v2
"""

import argparse
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]  # evaluation/<stage>/this file
EXTRACTION = REPO_ROOT / "output" / "article_extraction"
HERE = Path(__file__).resolve().parent
GOLD_PATH = HERE / "gold_article_list_test.csv"
# Gold volume names that differ from the pipeline's volume keys.
VOLUME_ALIASES = {"chambers_1840": "chambers_1839"}
MATCH = 0.7  # least similarity (0-1) for a run of words to count as found
PIECE_WORDS = 10  # words of a front/back-matter piece used to find it
PAGE_SLACK = 1  # pages either side of the gold item's pages searched
SMALL = {"the", "of", "and", "a", "an", "in", "on", "at", "to", "for", "by", "with", "from"}
CONTINUED = re.compile(r"\b(?:continued|concluded)\b|in our (?:first|last|former) (?:number|no)", re.I)
TO_BE_CONTINUED = re.compile(r"\bto be (?:continued|concluded)\b", re.I)
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august",
          "september", "october", "november", "december"]


# --- text helpers -----------------------------------------------------------

ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
ROMAN = re.compile(r"^M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})$")


def number_value(text) -> int | None:
    """An issue number in figures ("274") or Roman numerals ("CCLXXIV")."""
    text = str(text).strip().rstrip(".").upper()
    if text.isdigit():
        return int(text)
    if not text or not ROMAN.match(text):
        return None
    values = [ROMAN_VALUES[c] for c in text]
    return sum(-v if i + 1 < len(values) and v < values[i + 1] else v for i, v in enumerate(values))


def tokens(text) -> list[str]:
    """Lowercase word tokens, accents and ligatures folded (œ -> oe)."""
    if not isinstance(text, str) or not text:
        return []
    text = text.replace("œ", "oe").replace("Œ", "oe").replace("æ", "ae").replace("ſ", "s")
    text = re.sub(r"(?<=\w)['’](?=\w)", "", text)  # Year’s / YEAR'S -> years
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.findall(r"[a-z0-9]+", text.lower())


def find(needle: list[str], hay: list[str]) -> tuple[int, float]:
    """Best fuzzy position of a word run in a token list: (position, similarity)."""
    if not needle or not hay:
        return -1, 0.0
    n, anchors = len(needle), set(needle[:3])
    best = (-1, 0.0)
    if n <= 2:  # a short source has no exact word to anchor on if OCR slipped ("LOCKR.")
        word = "".join(needle)
        for i in range(len(hay)):
            for size in (1, 2):
                joined = "".join(hay[i:i + size])
                score = SequenceMatcher(None, word, joined, autojunk=False).ratio()
                if score > best[1]:
                    best = (i, score)
        return best
    for i, t in enumerate(hay):
        if t not in anchors:
            continue
        for start in range(max(0, i - 2), i + 1):
            for size in (n - 1, n, n + 1):
                window = hay[start:start + max(size, 1)]
                score = SequenceMatcher(None, needle, window, autojunk=False).ratio()
                if score > best[1]:
                    best = (start, score)
    return best


def same_words(a: str, b: str) -> bool:
    """Two titles / series names agree (case, punctuation, small OCR slips aside)."""
    ta, tb = tokens(a), tokens(b)
    if not ta and not tb:
        return True
    if not ta or not tb:
        return False
    ka = [t for t in ta if t not in SMALL] or ta
    kb = [t for t in tb if t not in SMALL] or tb
    # letter by letter, so one-letter OCR slips and plurals still agree
    # ("Fugitive Writing" / "FUGITIVE WRITINGS", "M. TURGOт")
    return SequenceMatcher(None, " ".join(ka), " ".join(kb), autojunk=False).ratio() >= 0.85 \
        or set(ka) <= set(kb) or set(kb) <= set(ka)


def pieces(text: str) -> list[str]:
    return [p.strip() for p in str(text).split("|") if p.strip()] if isinstance(text, str) else []


def is_footnote(piece: str) -> bool:
    return bool(re.match(r"^\s*[*†‡§]", piece))


def parse_date(text) -> tuple | None:
    """(month, day, year) from "6.18.1836", "June 18, 1836", or the end of a
    range: "5.31-6.30.1836". Month and year only ("8.1834"; pipeline v4
    "08-1834") give day None. Pipeline v4 dates are numeric: "08-30-1834"."""
    if not isinstance(text, str):
        return None
    m = re.fullmatch(r"\s*(\d{2})-(\d{2})(?:-(\d{4}))?\s*", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3)) if m.group(3) else None
    m = re.fullmatch(r"\s*(\d{1,2})[.-](\d{4})\s*", text)
    if m:
        return int(m.group(1)), None, int(m.group(2))
    text = text.split("-")[-1]
    m = re.match(r"^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})", text)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.search(r"([A-Za-z]+)\.?\s+(\d{1,2})(?:\s*,?\s*(\d{4}))?", text)
    if m and m.group(1).lower()[:3] in [x[:3] for x in MONTHS]:
        month = [x[:3] for x in MONTHS].index(m.group(1).lower()[:3]) + 1
        return month, int(m.group(2)), int(m.group(3)) if m.group(3) else None
    return None


def page_list(spec) -> list[int]:
    return [int(p) for p in str(spec).split(";") if p.strip().isdigit()] if isinstance(spec, str) else []


# --- loading ----------------------------------------------------------------

def load_gold(path: Path = GOLD_PATH) -> pd.DataFrame:
    gold = pd.read_csv(path, dtype=str, keep_default_na=False)
    if "notes" not in gold:  # v4 gold splits notes into figure and item notes
        gold["notes"] = gold.get("figure_notes", "") + " " + gold.get("item_notes", "")
    # The v2 gold called Chambers Vol. 8 "chambers_1840"; the v5 test's Chambers
    # really is 1840, so the alias applies to the v2 gold list only.
    aliases = VOLUME_ALIASES if Path(path).name == GOLD_PATH.name else {}
    gold["pipeline_volume"] = gold.volume.map(lambda v: aliases.get(v, v))
    gold["gold_id"] = gold.gold_id.astype(int)
    gold["article_type"] = gold.article_type.str.strip().str.replace(" ", "_")
    # An imprint may have no page: it is found by its words.
    gold["start_pdf_page"] = [int(p) if p.strip() else 0 for p in gold.start_pdf_page]
    gold["end_page"] = [int(e) if e.strip().isdigit() else s
                        for e, s in zip(gold.end_pdf_page, gold.start_pdf_page)]
    return gold


def load_pipeline(version: str, volume: str) -> dict:
    out = EXTRACTION / version / volume
    articles = pd.read_csv(out / f"{volume}_articles.csv")
    regions = pd.read_csv(out / f"{volume}_regions.csv")
    imprints = pd.read_csv(out / f"{volume}_imprints.csv")
    articles["page_list"] = articles.pages.map(page_list)
    for field in ("text", "title", "front_matter", "back_matter", "table_text"):
        articles[f"tok_{field}"] = articles[field].map(tokens)
    return {"articles": articles.set_index("article_id", drop=False),
            "regions": regions, "imprints": imprints}


# --- locating gold words in the output --------------------------------------

def locate(words: str, pipe: dict, pages: range) -> dict:
    """Where a gold word run is in the output: the article and field holding
    it (text / front_matter / back_matter / title / table_text), else the
    role of the box holding it, else nothing."""
    needle = tokens(words)
    result = {"article_id": None, "field": "not found", "pos": -1, "score": 0.0}
    if not needle:
        result["field"] = "no gold words"
        return result
    arts = pipe["articles"]
    nearby = arts[arts.page_list.map(lambda ps: any(p in pages for p in ps))]
    for field in ("text", "front_matter", "back_matter", "title", "table_text"):
        for aid, toks in nearby[f"tok_{field}"].items():
            pos, score = find(needle, toks)
            if score >= MATCH and score > result["score"] + (0.0 if field == "text" else 0.05):
                result = {"article_id": aid, "field": field, "pos": pos, "score": round(score, 2)}
        if result["field"] == "text":
            # The same words can also open another article ("It is well known
            # that" quoted mid-text, then opening the next article): an equal
            # match at an article's start wins (v4 test, Chambers 1837 p15).
            if result["pos"] > 0:
                for aid, toks in nearby["tok_text"].items():
                    pos, score = find(needle, toks)
                    if pos == 0 and score >= result["score"]:
                        return {"article_id": aid, "field": "text", "pos": 0, "score": round(score, 2)}
            return result  # text first: a run found in the text is where it is
    if result["article_id"]:
        return result
    regions = pipe["regions"]
    for r in regions[regions.page.isin(pages)].itertuples():
        pos, score = find(needle, tokens(r.text))
        if score >= MATCH and score > result["score"]:
            result = {"article_id": r.article_id if isinstance(r.article_id, str) else None,
                      "field": f"box role: {r.role}", "pos": pos, "score": round(score, 2)}
    return result


# --- scoring ----------------------------------------------------------------

def score(version: str = "v2", gold: pd.DataFrame | None = None) -> dict:
    gold = load_gold() if gold is None else gold
    item_rows, art_rows, imprint_rows, piece_rows = [], [], [], []
    for volume, g in gold.groupby("pipeline_volume", sort=False):
        pipe = load_pipeline(version, volume)
        arts = pipe["articles"]
        items = g[g.article_type.isin(["article", "editorial_notice"])].sort_values("gold_id")
        located = {}
        for row in items.itertuples():
            pages = range(row.start_pdf_page - PAGE_SLACK, row.end_page + PAGE_SLACK + 1)
            start = locate(row.first_words, pipe, pages)
            end = locate(row.last_words, pipe, pages) if row.last_words.strip() else \
                {"article_id": None, "field": "no gold words", "pos": -1, "score": 0.0}
            located[row.gold_id] = (row, start, end)

        starts_in = {}  # pipeline article -> gold items whose first words open... are in its text
        for gid, (row, start, end) in located.items():
            if start["field"] == "text":
                starts_in.setdefault(start["article_id"], []).append(gid)

        ordered = list(located)
        for k, gid in enumerate(ordered):
            row, start, end = located[gid]
            a_id = start["article_id"] if start["field"] == "text" else None
            prev_gid = ordered[k - 1] if k else None
            next_gid = ordered[k + 1] if k + 1 < len(ordered) else None
            merged_prev = bool(a_id) and prev_gid is not None and gid in starts_in.get(a_id, []) \
                and prev_gid in starts_in.get(a_id, [])
            merged_next = bool(a_id) and next_gid is not None and next_gid in starts_in.get(a_id, [])
            split = bool(a_id) and end["field"] == "text" and end["article_id"] != a_id
            if not a_id:
                status = "lost"
            elif merged_prev or merged_next:
                status = "merged" + ("+split" if split else "")
            elif split:
                status = "split"
            else:
                status = "exact"
            own = bool(a_id) and not merged_prev  # it opens its own pipeline article
            art = arts.loc[a_id] if a_id else None
            rec = {
                "volume": row.volume, "gold_id": gid, "issue_no": row.issue_no,
                "start_pdf_page": row.start_pdf_page, "article_type": row.article_type,
                "gold_title": row.title, "status": status,
                "merged_with": ";".join(str(x) for x in starts_in.get(a_id, []) if x != gid) if a_id else "",
                "start_found_in": start["field"], "start_article_id": start["article_id"],
                "start_score": start["score"], "start_offset": start["pos"],
                "end_found_in": end["field"], "end_article_id": end["article_id"],
                "pipeline_title": art.title if own and isinstance(art.title, str) else "",
                "opens_own_article": own,
            }
            if own:
                span = item_span(arts, a_id, end["article_id"] if end["field"] == "text" else None)
                rec["pipeline_articles"] = ";".join(span)
                rec.update(score_fields(row, combine(arts, span), piece_rows))
            item_rows.append(rec)

        for aid, art in arts.iterrows():
            held = starts_in.get(aid, [])
            ends_here = [gid for gid, (_, _, e) in located.items()
                         if e["field"] == "text" and e["article_id"] == aid]
            art_rows.append({
                "volume": volume, "article_id": aid, "pipeline_title": art.title,
                "pages": art.pages, "word_count": art.word_count,
                "gold_starts": ";".join(map(str, held)), "n_gold_starts": len(held),
                "gold_ends": ";".join(map(str, ends_here)),
                "status": "matched" if len(held) == 1 else ("merged" if held else "extra"),
                "text_start": " ".join(str(art.text).split()[:12]) if isinstance(art.text, str) else "",
            })

        imprint_rows += score_imprints(g, pipe, volume)

    return {"volume_map": dict(zip(gold.volume, gold.pipeline_volume)),
            "items": pd.DataFrame(item_rows), "pipeline_articles": pd.DataFrame(art_rows),
            "imprints": pd.DataFrame(imprint_rows), "pieces": pd.DataFrame(piece_rows)}


def item_span(arts: pd.DataFrame, first: str, last: str | None) -> list[str]:
    """The pipeline articles a gold item runs through: its first article, and
    when it was split, every article up to the one holding its last words."""
    ids = list(arts.index)
    i = ids.index(first)
    j = ids.index(last) if last in ids and ids.index(last) > i else i
    return ids[i:j + 1]


def combine(arts: pd.DataFrame, span: list[str]) -> pd.Series:
    """One view of an item split over several pipeline articles: title,
    series, type and issue from the first; front matter from the first; back
    matter, text and figures from all (a fragment's back matter is still back
    matter, though the split is counted as a boundary error)."""
    first, parts = arts.loc[span[0]].copy(), arts.loc[span]
    for field in ("text", "back_matter", "table_text"):
        first[f"tok_{field}"] = [t for toks in parts[f"tok_{field}"] for t in toks]
        first[field] = " | ".join(str(x) for x in parts[field] if isinstance(x, str))
    first["n_figures"] = int(parts.n_figures.sum())
    return first


def score_fields(row, art, piece_rows: list) -> dict:
    """Title, front/back matter, series, continuation, type, figures, issue."""
    out = {}
    gold_title, pipe_title = row.title.strip(), art.title if isinstance(art.title, str) else ""
    if not gold_title and not pipe_title:
        out["title_result"] = "both untitled"
    elif gold_title and not pipe_title:
        out["title_result"] = "missing"
    elif not gold_title:
        out["title_result"] = "extra (gold untitled)"
    else:
        out["title_result"] = "correct" if same_words(gold_title, pipe_title) else "wrong"

    for field in ("front_matter", "back_matter"):
        found = 0
        gold_pieces = pieces(getattr(row, field))
        for p in gold_pieces:
            needle = tokens(p)[:PIECE_WORDS]
            where = "missing"
            for place in (field, "text", "front_matter" if field == "back_matter" else "back_matter",
                          "table_text", "title"):
                pos, s = find(needle, art[f"tok_{place}"])
                if s >= MATCH:
                    where = "in place" if place == field else f"in {place}"
                    break
            found += where == "in place"
            piece_rows.append({"volume": row.volume, "gold_id": row.gold_id, "field": field,
                               "footnote": is_footnote(p), "piece": p, "result": where})
        pipe_pieces = pieces(art[field])
        extra = [p for p in pipe_pieces
                 if not any(find(tokens(p)[:PIECE_WORDS], tokens(gp))[1] >= MATCH
                            or find(tokens(gp)[:PIECE_WORDS], tokens(p))[1] >= MATCH
                            for gp in gold_pieces)]
        out[f"{field}_gold"] = len(gold_pieces)
        out[f"{field}_found"] = found
        out[f"{field}_extra"] = len(extra)
        out[f"{field}_pipeline"] = " | ".join(pipe_pieces)

    gold_series, pipe_series = row.series.strip(), art.series if isinstance(art.series, str) else ""
    out["series_result"] = (
        ("correct" if same_words(gold_series, pipe_series) else "wrong") if gold_series and pipe_series
        else "missing" if gold_series else "extra" if pipe_series else "none (both)")
    out["pipeline_series"] = pipe_series

    gold_cf = bool(row.continued_from.strip())
    pipe_cf = bool(art.get("continued_from", False)) or isinstance(art.continues_article_id, str) \
        or bool(CONTINUED.search(str(art.front_matter) if isinstance(art.front_matter, str) else ""))
    out["continued_from_result"] = agreement(gold_cf, pipe_cf)
    gold_tbc = bool(row.to_be_continued.strip())
    pipe_tbc = bool(art.get("to_be_continued", False)) or bool(
        TO_BE_CONTINUED.search(str(art.back_matter) if isinstance(art.back_matter, str) else ""))
    out["to_be_continued_result"] = agreement(gold_tbc, pipe_tbc)
    out["type_result"] = agreement(row.article_type == "editorial_notice",
                                   art.article_type == "editorial_notice")
    gold_figs = len(re.findall(r"\bfig:", row.notes))
    out["figures_gold"], out["figures_pipeline"] = gold_figs, int(art.n_figures)
    out["figures_result"] = "correct" if gold_figs == int(art.n_figures) else "wrong"
    out["pipeline_issue_no"] = "" if pd.isna(art.issue_no) else str(int(art.issue_no))
    gold_no = number_value(row.issue_no)  # the gold may give it in Roman numerals (v5)
    gold_no = str(gold_no) if gold_no is not None else row.issue_no.strip()
    out["issue_no_result"] = "correct" if out["pipeline_issue_no"] == gold_no else \
        ("missing" if not out["pipeline_issue_no"] else "wrong")
    gd, pdt = parse_date(row.issue_date), parse_date(art.issue_date)
    out["pipeline_issue_date"] = art.issue_date if isinstance(art.issue_date, str) else ""
    out["issue_date_result"] = "missing" if not pdt else (
        "correct" if gd and pdt[:2] == gd[:2] and (pdt[2] in (None, gd[2])) else "wrong")
    return out


def agreement(gold: bool, pipe: bool) -> str:
    return {(True, True): "correct (yes)", (False, False): "correct (no)",
            (True, False): "missing", (False, True): "extra"}[(gold, pipe)]


def score_imprints(g: pd.DataFrame, pipe: dict, volume: str) -> list[dict]:
    """Gold imprint rows vs the pipeline's imprint for the same issue (issues
    matched in order: the n-th gold issue is the pipeline's issue_seq n)."""
    rows = []
    issues = list(dict.fromkeys(g.sort_values("gold_id").issue_no))
    imprints = pipe["imprints"].set_index("issue_seq")
    for row in g[g.article_type == "imprint"].sort_values("gold_id").itertuples():
        seq = issues.index(row.issue_no) + 1
        text = imprints.imprint_text.get(seq) if seq in imprints.index else None
        text = text if isinstance(text, str) else None
        hay = tokens(text)
        first = find(tokens(row.first_words), hay)[1] >= MATCH
        last = find(tokens(row.last_words), hay)[1] >= MATCH if row.last_words.strip() else True
        result = "complete" if first and last else "partial" if first or last else "missing"
        where = ""
        if result != "complete":
            pages = range(row.start_pdf_page - PAGE_SLACK, row.end_page + PAGE_SLACK + 1)
            where = locate(row.first_words if not first else row.last_words, pipe, pages)["field"]
        rows.append({"volume": row.volume, "gold_id": row.gold_id, "issue_no": row.issue_no,
                     "issue_seq": seq, "result": result, "first_found": first, "last_found": last,
                     "missing_part_found_in": where,
                     "pipeline_imprint": (text or "")[:160]})
    return rows


# --- summary ----------------------------------------------------------------

def rate(n: int, d: int) -> str:
    return f"{n}/{d} ({100 * n / d:.0f}%)" if d else "–"


def summary_tables(res: dict) -> dict:
    items, arts = res["items"], res["pipeline_articles"]
    vols = list(dict.fromkeys(items.volume))
    t = {}
    rows = {}
    for v in vols + ["all"]:
        it = items if v == "all" else items[items.volume == v]
        pa = arts if v == "all" else arts[arts.volume == res.get("volume_map", {}).get(v, v)]
        n = len(it)
        rows[v] = {
            "gold items": n,
            "pipeline articles": len(pa),
            "exact": rate((it.status == "exact").sum(), n),
            "merged": rate(it.status.str.startswith("merged").sum(), n),
            "split": rate((it.status == "split").sum(), n),
            "lost": rate((it.status == "lost").sum(), n),
            "boundary recall": rate(int(it.opens_own_article.sum()), n),
            "boundary precision": rate(int((pa.n_gold_starts > 0).sum()), len(pa)),
            "extra pipeline articles": int((pa.status == "extra").sum()),
        }
    t["items"] = pd.DataFrame(rows)

    own = items[items.opens_own_article]
    field_rows = {}
    for v in vols + ["all"]:
        o = own if v == "all" else own[own.volume == v]
        title_ok = o.title_result.isin(["correct", "both untitled"]).sum()
        fm_g, fm_f = int(o.front_matter_gold.sum()), int(o.front_matter_found.sum())
        bm_g, bm_f = int(o.back_matter_gold.sum()), int(o.back_matter_found.sum())
        ser = o[o.series_result != "none (both)"]
        field_rows[v] = {
            "items scored (open their own article)": len(o),
            "title": rate(title_ok, len(o)),
            "front matter pieces in place": rate(fm_f, fm_g),
            "back matter pieces in place": rate(bm_f, bm_g),
            "series (where either has one)": rate((ser.series_result == "correct").sum(), len(ser)),
            "continued from": rate(o.continued_from_result.str.startswith("correct").sum(), len(o)),
            "to be continued": rate(o.to_be_continued_result.str.startswith("correct").sum(), len(o)),
            "editorial notice / article": rate(o.type_result.str.startswith("correct").sum(), len(o)),
            "illustration count": rate((o.figures_result == "correct").sum(), len(o)),
            "issue number": rate((o.issue_no_result == "correct").sum(), len(o)),
            "issue date": rate((o.issue_date_result == "correct").sum(), len(o)),
        }
    t["fields"] = pd.DataFrame(field_rows)

    p = res["pieces"]
    if len(p):
        p = p.assign(kind=p.field.str.replace("_", " ") + p.footnote.map({True: " (footnote)", False: ""}))
        t["pieces"] = pd.crosstab(p.kind, p.result, margins=True, margins_name="total")
    imp = res["imprints"]
    if len(imp):
        t["imprints"] = pd.crosstab(imp.volume, imp.result, margins=True, margins_name="total")
    return t


def write(res: dict, version: str, out_dir: Path, gold_path: Path = GOLD_PATH) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in res.items():
        if isinstance(df, pd.DataFrame):  # not the volume map
            df.to_csv(out_dir / f"{version}_gold_comp_eval_{name}.csv", index=False)
    t = summary_tables(res)
    lines = [f"# {version} scored against the gold article list", "",
             "Written by `evaluation/evaluating_v2_article_extraction/score_gold.py`; definitions in its docstring. Gold list:",
             f"`{gold_path.resolve().relative_to(REPO_ROOT)}` (annotated from the printed pages only).", ""]
    titles = {"items": "Items and boundaries", "fields": "Fields (items that open their own article)",
              "pieces": "Front / back matter pieces", "imprints": "Imprints"}
    for key, df in t.items():
        lines += [f"## {titles[key]}", "", df.to_markdown(), ""]
    path = out_dir / f"{version}_gold_comp_eval_summary.md"
    path.write_text("\n".join(lines))
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", default="v2")
    parser.add_argument("--out", type=Path, default=HERE)
    parser.add_argument("--gold", type=Path, default=GOLD_PATH)
    args = parser.parse_args()
    res = score(args.version, load_gold(args.gold))
    path = write(res, args.version, args.out, args.gold)
    print(path.read_text())


if __name__ == "__main__":
    main()
