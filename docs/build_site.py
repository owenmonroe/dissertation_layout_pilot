"""Build the data for the public topic site (docs/, served by GitHub Pages).

Reads the final topic model and the frozen v6 extraction, and writes:
    docs/data/topics.json             the 16 topics, each with its top 3 articles
    docs/data/articles/<id>.json      one per article: text, figures, closest
                                      article, topics in its issue
    docs/figures/<file>.jpg           figures resized for the web

Run from the repository root, in the topicmodel-env environment:
    python docs/build_site.py

Rerun after relabelling topics or rerunning the model.
"""
import json
import re
import shutil
import sqlite3
from pathlib import Path

import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "output/topic_models/v6/bertopic_k16/topics.sqlite"
LABELS = ROOT / "output/topic_models/v6/bertopic_k16/topics.csv"   # Owen's labels
EXTRACTION = ROOT / "output/article_extraction/v6/articles.sqlite"
OUT = ROOT / "docs"

TOP_ARTICLES = 3        # articles shown per topic
ISSUE_SHARE = 0.05      # topics listed for an issue: at least this share of its words
MIX_WEIGHT = 0.05       # an article's topics listed at this weight or more
FIGURE_WIDTH = 900      # figures resized to at most this width (pixels)
MAX_FIGURES = 3         # figures shown on an article page

MAGAZINES = {"chambers": "Chambers's Edinburgh Journal", "penny": "The Penny Magazine",
             "saturday": "The Saturday Magazine"}
COLUMNS = ["left", "middle", "right", "spanning"]


def load():
    t = sqlite3.connect(RUN)
    e = sqlite3.connect(EXTRACTION)
    topics = pd.read_sql("SELECT * FROM topics", t).set_index("topic_id")
    arts = pd.read_sql("SELECT * FROM articles WHERE modelled = 1", t).set_index("doc_id")
    mix = pd.read_sql("SELECT * FROM article_topics", t)
    boxes = pd.read_sql("SELECT * FROM box_topics", t)
    issues = pd.read_sql("SELECT * FROM issue_topics", t)
    text = pd.read_sql("SELECT volume, article_id, text FROM articles", e)
    figs = pd.read_sql("SELECT volume, page, article_id, image_file, caption, y1 "
                       "FROM regions WHERE role = 'figure'", e)
    return topics, arts, mix, boxes, issues, text, figs


def relation(col_a, col_b):
    if col_a == col_b:
        return "same column"
    if "spanning" in (col_a, col_b):
        return "same page"
    if abs(COLUMNS.index(col_a) - COLUMNS.index(col_b)) == 1:
        return "neighbouring column"
    return "same page"


def closest(doc, arts, boxes, issue_order):
    """The article nearest in reading order on the same page; if the article is
    alone on its pages, the next (or previous) article in the issue."""
    mine = boxes[boxes.doc_id == doc]
    best = None
    for pg, b in mine.groupby("page"):
        others = boxes[(boxes.volume == b.volume.iloc[0]) & (boxes.page == pg)
                       & (boxes.doc_id != doc) & boxes.doc_id.isin(arts.index)]
        for o in others.itertuples():
            gaps = (b.reading_order - o.reading_order).abs()
            i = gaps.idxmin()
            key = (gaps[i], o.words * -1)
            if best is None or key < best[0]:
                best = (key, o.doc_id, relation(b.column[i], o.column))
    if best:
        return best[1], best[2]
    order = issue_order[arts.volume[doc], arts.issue_seq[doc]]
    i = order.index(doc)
    if i + 1 < len(order):
        return order[i + 1], "next article in the issue"
    if i > 0:
        return order[i - 1], "previous article in the issue"
    return None, None


def figure_out(path, name):
    """Copy a figure into docs/figures at web size; returns its site path."""
    src = ROOT / path
    dest = OUT / "figures" / name
    if not dest.exists():
        im = Image.open(src).convert("RGB")
        if im.width > FIGURE_WIDTH:
            im = im.resize((FIGURE_WIDTH, round(im.height * FIGURE_WIDTH / im.width)))
        im.save(dest, "JPEG", quality=78, optimize=True)
    return f"figures/{name}"


def main():
    topics, arts, mix, boxes, issues, text, figs = load()
    text = dict(zip(text.volume + "/" + text.article_id, text.text))
    labels = pd.read_csv(LABELS, keep_default_na=False).set_index("topic_id").label
    label = {t: labels.get(t, "").strip() or f"Topic {t}" for t in topics.index}
    mix = mix[mix.doc_id.isin(arts.index)]

    # Reading order of each issue's articles, from their first box.
    first = boxes.sort_values(["page", "reading_order"]).groupby("doc_id").first()
    arts["_page"] = first.page.reindex(arts.index).fillna(arts.start_page)
    arts["_order"] = first.reading_order.reindex(arts.index).fillna(0)
    issue_order = {k: list(g.sort_values(["_page", "_order"]).index)
                   for k, g in arts.groupby(["volume", "issue_seq"])}

    def summary(d):
        a = arts.loc[d]
        return {"id": a.article_id, "title": title(a, text.get(d, "")),
                "magazine": MAGAZINES[a.magazine], "issue": str(a.issue_no),
                "date": a.issue_date, "pages": pages(a), "topic": int(a.main_topic),
                "us_reprint": bool(a.us_reprint)}

    # Topics, each with its top articles by words on the topic.
    mix["topic_words"] = mix.weight * mix.doc_id.map(arts.word_count)
    out_topics = []
    for t, r in topics.iterrows():
        top = mix[mix.topic_id == t].sort_values("topic_words", ascending=False).head(TOP_ARTICLES)
        out_topics.append({
            "id": int(t), "label": label[t], "words": r.top_words.split()[:8],
            "share": round(r.share_of_words, 4), "n_main": int(r.n_articles_main),
            "articles": [dict(summary(d), topic_share=round(w, 3))
                         for d, w in zip(top.doc_id, top.weight)]})

    # One file per article.
    (OUT / "data/articles").mkdir(parents=True, exist_ok=True)
    (OUT / "figures").mkdir(exist_ok=True)
    figs["caption"] = figs.caption.fillna("")
    figs["doc_id"] = figs.volume + "/" + figs.article_id.fillna("")
    for d, a in arts.iterrows():
        near, rel = closest(d, arts, boxes, issue_order)
        own = figs[figs.doc_id == d].sort_values(["page", "y1"])
        figures = [{"src": figure_out(f.image_file, Path(f.image_file).name),
                    "caption": (f.caption or "").strip(), "with": None}
                   for f in own.head(MAX_FIGURES).itertuples()]
        if not figures:  # a figure printed on the same page, belonging to another article
            pg = range(int(a.start_page), int(a.end_page) + 1)
            near_figs = figs[(figs.volume == a.volume) & figs.page.isin(pg)].sort_values("y1")
            for f in near_figs.head(MAX_FIGURES).itertuples():
                figures.append({"src": figure_out(f.image_file, Path(f.image_file).name),
                                "caption": (f.caption or "").strip(),
                                "with": summary(f.doc_id)["title"] if f.doc_id in arts.index else None})
        iss = issues[(issues.volume == a.volume) & (issues.issue_seq == a.issue_seq)
                     & (issues.share >= ISSUE_SHARE)].sort_values("share", ascending=False)
        m = mix[(mix.doc_id == d) & (mix.weight >= MIX_WEIGHT)].sort_values("weight", ascending=False)
        record = dict(
            summary(d), words=int(a.word_count),
            mix=[{"topic": int(r.topic_id), "weight": round(r.weight, 3)} for r in m.itertuples()],
            text=[p.strip() for p in text.get(d, "").split("\n") if p.strip()],
            figures=figures,
            closest=dict(summary(near), relation=rel) if near else None,
            issue_topics=[{"topic": int(r.topic_id), "share": round(r.share, 3)}
                          for r in iss.itertuples()],
            issue_articles=len(issue_order[a.volume, a.issue_seq]))
        (OUT / "data/articles" / f"{a.article_id}.json").write_text(
            json.dumps(record, ensure_ascii=False))

    meta = {"articles": len(arts), "issues": int(arts.groupby(["volume", "issue_seq"]).ngroups),
            "words": int(arts.word_count.sum()),
            "years": [int(arts.year.min()), int(arts.year.max())]}
    (OUT / "data/topics.json").write_text(
        json.dumps({"meta": meta, "topics": out_topics}, ensure_ascii=False, indent=1))
    n_figs = len(list((OUT / "figures").glob("*.jpg")))
    size = sum(f.stat().st_size for f in (OUT / "figures").glob("*.jpg")) / 1e6
    print(f"{len(out_topics)} topics, {len(arts)} articles, {n_figs} figures ({size:.1f} MB)")


SMALL = {"a", "an", "and", "as", "at", "by", "for", "from", "in", "of", "on", "or",
         "the", "to", "with"}


def title(a, body):
    """Printed titles are mostly in capitals: set them in title case, keeping
    roman numerals, and drop stray quotation marks and asterisks."""
    t = re.sub(r'[*"“”]', "", a.title or "").strip(" .-—")
    if not t:
        return "Untitled: " + " ".join(body.split()[:6]) + "…"
    words = re.split(r"(\s+|-|—)", t.lower())
    out = []
    for i, w in enumerate(words):
        core = w.strip(".,;:()'")
        if re.fullmatch(r"i{1,3}|iv|vi{0,3}|ix|xi{0,3}|xi?v|xvi{0,3}", core):  # roman numeral
            w = w.upper()
        elif core in SMALL and i:
            pass
        else:
            w = re.sub(r"^([^a-z]*)([a-z])", lambda m: m.group(1) + m.group(2).upper(), w)
        out.append(w)
    return "".join(out)


def pages(a):
    s, e = int(a.start_page), int(a.end_page)
    return f"p. {s}" if s == e else f"pp. {s}–{e}"


if __name__ == "__main__":
    main()
