"""Explore one topic of the final topic model: where it is strongest, and what
sits with it.

    from topic_explorer import explore
    explore(9)

For a topic it shows:
1. the topic: name, top words, size;
2. its strongest issue, the article carrying it there, and every other topic
   in that issue with its articles, marked
   - "same article" (the topics meld inside one article), or
   - "separate article" (juxtaposition within the issue);
3. its strongest page that also holds another topic, column by column, with
   the partner articles marked same column / neighbouring column / same page;
4. its partner topics across all issues (topic_pairs_issue), with the
   partner's article titles in the issues they share.

Shares are shares of body-text words (see topic_examples_walkthrough.md).
"""
import re
import sqlite3
from pathlib import Path

import pandas as pd
from IPython.display import Markdown, display

ROOT = Path(__file__).resolve().parents[2]
RUN = ROOT / "output/topic_models/v6/bertopic_k16"
CORPUS = ROOT / "output/topic_models/v6/corpus/articles_corpus.csv"

# Suggested names; a label written in topics.label takes precedence.
SUGGESTED_NAMES = {
    0: "Tales and domestic fiction", 1: "Population, public improvements, education",
    2: "Knowledge, books and self-improvement", 3: "Towers, kings and earls",
    4: "Ballads, songs and Christmas", 5: "Ice, timber and glaciers",
    6: "Sea voyages and islands", 7: "Art and engraving", 8: "Plants and insects",
    9: "Animals", 10: "Shipping and Trinity House", 11: "French aristocratic tales",
    12: "Mythology", 13: "Plague and quack medicine", 14: "Chess problems", 15: "Archery",
}
# A partner topic counts in an issue or on a page at this share or more.
PARTNER_SHARE = 0.05
# An article "carries" a topic when the topic is at least this share of it.
CARRIES = 0.10
MAGAZINES = {"chambers": "Chambers's Edinburgh Journal", "penny": "Penny Magazine",
             "saturday": "Saturday Magazine"}
COLUMNS = ["left", "middle", "right", "spanning"]

_con = sqlite3.connect(RUN / "topics.sqlite")
_q = lambda sql, *p: pd.read_sql(sql, _con, params=p)
TOPICS = _q("SELECT * FROM topics").set_index("topic_id")
ARTICLES = _q("SELECT * FROM articles").set_index("doc_id")
ART_TOPICS = _q("SELECT * FROM article_topics")
BOXES = _q("SELECT * FROM box_topics")
ISSUES = _q("SELECT * FROM issue_topics")
PAGES = _q("SELECT * FROM page_topics")
PAIRS = _q("SELECT * FROM topic_pairs_issue")
_opening = pd.read_csv(CORPUS, keep_default_na=False).set_index("doc_id").text


def name(t: int) -> str:
    label = TOPICS.label.get(t)
    return label if isinstance(label, str) and label.strip() else SUGGESTED_NAMES.get(t, f"Topic {t}")


def tag(t: int) -> str:
    return f"{t} · {name(t)}"


def title(doc_id: str) -> str:
    """The printed title, or the opening words of an untitled piece."""
    t = ARTICLES.title.get(doc_id)
    if isinstance(t, str) and t.strip():
        t = t.strip().strip('"').lower()
        return re.sub(r"(^|[\s\-(\.])([a-z])", lambda m: m.group(1) + m.group(2).upper(), t)
    words = _opening.get(doc_id, "").split()[:7]
    return "(untitled) " + " ".join(words) + "…"


def issue_name(volume: str, seq: int) -> str:
    a = ARTICLES[(ARTICLES.volume == volume) & (ARTICLES.issue_seq == seq)].iloc[0]
    return f"{MAGAZINES[a.magazine]}, No. {a.issue_no}, {a.issue_date}"


def _md(text: str):
    display(Markdown(text))


def _table(df: pd.DataFrame):
    display(df.style.hide(axis="index").format(precision=2))


def topic_words_in(doc_ids, t: int) -> pd.Series:
    """Words of topic t in each article (from its boxes)."""
    b = BOXES[BOXES.doc_id.isin(doc_ids) & (BOXES.topic_id == t)]
    return b.groupby("doc_id").words.sum().sort_values(ascending=False)


# --- 1. The topic ---------------------------------------------------------------

def overview(t: int):
    r = TOPICS.loc[t]
    _md(f"# Topic {tag(t)}\n\n"
        f"**Top words:** {r.top_words}\n\n"
        f"**Articles mainly on it:** {r.n_articles_main} · **share of all words:** "
        f"{r.share_of_words:.1%} · **text boxes:** {r.n_boxes}")


# --- 2. Strongest issue -----------------------------------------------------------

def strongest_issue(t: int, rank: int = 0):
    """The issue where topic t has its largest share (rank 0 = strongest)."""
    row = ISSUES[ISSUES.topic_id == t].sort_values("share", ascending=False).iloc[rank]
    vol, seq = row.volume, int(row.issue_seq)
    docs = ARTICLES[(ARTICLES.volume == vol) & (ARTICLES.issue_seq == seq)].index
    carriers = topic_words_in(docs, t)
    lead = carriers.index[0]

    _md(f"## Strongest issue: {issue_name(vol, seq)}\n\n"
        f"Topic {t} is **{row.share:.0%}** of the issue ({row.words:,.0f} words).\n\n"
        f"**Article carrying it most:** *{title(lead)}* (p{ARTICLES.start_page[lead]}): "
        f"{carriers.iloc[0]:,} words of topic {t}, "
        f"{carriers.iloc[0] / ARTICLES.word_count[lead]:.0%} of the article.")
    others = [d for d in carriers.index[1:]]
    if others:
        _md("Other articles carrying it: " + "; ".join(
            f"*{title(d)}* (p{ARTICLES.start_page[d]}, {carriers[d]:,} words)" for d in others))

    rows = []
    partners = ISSUES[(ISSUES.volume == vol) & (ISSUES.issue_seq == seq) & (ISSUES.topic_id != t)
                      & (ISSUES.share >= PARTNER_SHARE)].sort_values("share", ascending=False)
    t_docs = set(carriers.index)
    for p in partners.itertuples():
        pw = topic_words_in(docs, p.topic_id)
        for d, w in pw.items():
            if w / ARTICLES.word_count[d] < CARRIES:
                continue
            rows.append({"partner topic": tag(p.topic_id), "share of issue": p.share,
                         "article": title(d), "page": ARTICLES.start_page[d],
                         "partner's share of article": w / ARTICLES.word_count[d],
                         "relation": "same article (meld)" if d in t_docs and
                         topic_words_in([d], t).sum() / ARTICLES.word_count[d] >= CARRIES
                         else "separate article (juxtaposition)"})
    _md(f"**Partner topics in this issue** (each at least {PARTNER_SHARE:.0%} of the issue; "
        f"articles listed where the partner is at least {CARRIES:.0%} of the article):")
    _table(pd.DataFrame(rows))


# --- 3. Strongest page with a partner ---------------------------------------------

def _relation(col_a: str, col_b: str) -> str:
    if col_a == col_b:
        return "juxtaposition: same column"
    if "spanning" in (col_a, col_b):
        return "juxtaposition: same page (spanning)"
    if abs(COLUMNS.index(col_a) - COLUMNS.index(col_b)) == 1:
        return "juxtaposition: neighbouring column"
    return "juxtaposition: same page"


def _partner_pages(t: int, need: str) -> set:
    """Pages holding another topic at PARTNER_SHARE or more of the page's words:
    need="article": in an article that doesn't carry topic t (juxtaposition);
    need="topic": in any article, including t's own (meld or juxtaposition)."""
    b = BOXES.copy()
    totals = b.groupby(["volume", "page"]).words.sum()
    carriers = set(b[b.topic_id == t].doc_id)
    if need == "article":
        b = b[~b.doc_id.isin(carriers)]
    other = b[b.topic_id != t].groupby(["volume", "page", "topic_id"]).words.sum().reset_index()
    other["share"] = other.words / [totals[(v, p)] for v, p in zip(other.volume, other.page)]
    other = other[other.share >= PARTNER_SHARE]
    return set(zip(other.volume, other.page))


def strongest_page(t: int, rank: int = 0, need: str = "article"):
    """The page where topic t has its largest share among pages that also hold
    another topic (at least PARTNER_SHARE of the page):
    need="article" (default): the other topic is in a separate article, so the
    page shows juxtaposition; need="topic": any other topic, including inside
    t's own article (meld); need=None: any page."""
    pages = PAGES[PAGES.topic_id == t].copy()
    if need:
        keys = _partner_pages(t, need)
        pages = pages[[k in keys for k in zip(pages.volume, pages.page)]]
    if pages.empty:
        _md(f"## No page holds topic {t} beside another {'article' if need == 'article' else 'topic'}.")
        return
    row = pages.sort_values(["share", "words"], ascending=False).iloc[rank]
    vol, seq, pg = row.volume, int(row.issue_seq), int(row.page)
    b = BOXES[(BOXES.volume == vol) & (BOXES.page == pg)]
    share = PAGES[(PAGES.volume == vol) & (PAGES.issue_seq == seq) & (PAGES.page == pg)]

    label = {"article": " beside another article", "topic": " beside another topic", None: ""}[need]
    _md(f"## Strongest page{label}: "
        f"{issue_name(vol, seq)}, page {pg}\n\n"
        f"Topic {t} is **{row.share:.0%}** of the page ({row.words:,.0f} words).\n\n"
        "Page topics: " + "; ".join(f"{tag(r.topic_id)} {r.share:.0%}" for r in
                                     share.sort_values("share", ascending=False).itertuples()))

    # The page column by column: each article's stretch of boxes, in reading order.
    b = b.sort_values(["reading_order", "chunk"])
    run_id = ((b.column != b.column.shift()) | (b.doc_id != b.doc_id.shift())
              | (b.topic_id != b.topic_id.shift())).cumsum()
    runs = (b.groupby(run_id).agg(column=("column", "first"), doc_id=("doc_id", "first"),
                                  topic_id=("topic_id", "first"), words=("words", "sum"))
             .reset_index(drop=True))
    layout = pd.DataFrame({"column": runs.column, "article": runs.doc_id.map(title),
                           "topic": runs.topic_id.map(tag), "words": runs.words})
    _md("**The page in reading order** (runs of boxes of one article and one topic):")
    _table(layout)

    # Partner articles and how they sit relative to the topic's articles.
    mine = runs[runs.topic_id == t]
    rows = []
    for p in runs[runs.topic_id != t].itertuples():
        if p.words < 20:
            continue
        same = p.doc_id in set(mine.doc_id)
        rel = "same article (meld)" if same else min(
            (_relation(p.column, m.column) for m in mine.itertuples()),
            key=["juxtaposition: same column", "juxtaposition: neighbouring column",
                 "juxtaposition: same page (spanning)", "juxtaposition: same page"].index)
        rows.append({"partner topic": tag(p.topic_id), "partner article": title(p.doc_id),
                     "column": p.column, "words": p.words,
                     f"topic {t} article(s) beside it": "; ".join(sorted({title(d) for d in mine.doc_id})),
                     "relation": rel})
    _md("**Partner topics on this page:**")
    rows = pd.DataFrame(rows)
    if not rows.empty:
        rows = (rows.groupby(["partner topic", "partner article", "column",
                              f"topic {t} article(s) beside it", "relation"], sort=False)
                    .words.sum().reset_index())
    _table(rows)


# --- 4. Partner topics across all issues ---------------------------------------------

def partners(t: int, n: int = 5, titles: int = 3):
    """The topics most often present in the same issues as t, with the
    partner's article titles in those shared issues."""
    p = PAIRS[(PAIRS.topic_a == t) | (PAIRS.topic_b == t)].copy()
    p["partner"] = p.topic_a.where(p.topic_b == t, p.topic_b)
    p = p[p.together > 0].sort_values(["together", "lift"], ascending=False).head(n)
    present = ISSUES[ISSUES.share >= 0.10]
    mine = set(zip(present[present.topic_id == t].volume, present[present.topic_id == t].issue_seq))
    rows = []
    for r in p.itertuples():
        shared = mine & set(zip(present[present.topic_id == r.partner].volume,
                                present[present.topic_id == r.partner].issue_seq))
        docs = ARTICLES[[k in shared for k in zip(ARTICLES.volume, ARTICLES.issue_seq)]].index
        w = topic_words_in(docs, r.partner)
        main = w[[w[d] / ARTICLES.word_count[d] >= 0.5 for d in w.index]]  # mainly on the partner
        w = main if len(main) else w[[w[d] / ARTICLES.word_count[d] >= CARRIES for d in w.index]]
        rows.append({"partner topic": tag(r.partner), "issues together": r.together,
                     "lift": r.lift,
                     "partner's articles in those issues": "; ".join(
                         f"{title(d)} ({ARTICLES.magazine[d].title()} {ARTICLES.issue_no[d]})"
                         for d in w.index[:titles])})
    _md(f"## Partner topics across all issues\n\n"
        f"Topic {t} is present (at least 10% of the words) in **{len(mine)}** of 45 issues. "
        "Issues together: issues where both are present. Lift above 1: together more often than "
        "chance. Titles: the partner's articles in those shared issues with the most words on it "
        f"(mainly on the partner where there are any, otherwise carrying it at {CARRIES:.0%} or more).")
    _table(pd.DataFrame(rows))


# --- 5. Melds: one article holding topic t and another topic --------------------------

def melds(t: int, other: int = None, min_share: float = 0.25, min_words: int = 300, n: int = 10):
    """Articles where topic t and another topic each hold at least min_share of
    the article's words (other=None: any other topic). Longest articles first."""
    w = ART_TOPICS.pivot_table(index="doc_id", columns="topic_id", values="weight", fill_value=0)
    w = w[(w.get(t, 0) >= min_share)]
    rows = []
    for d, r in w.iterrows():
        if ARTICLES.word_count[d] < min_words:
            continue
        for o, ow in r.items():
            if o == t or ow < min_share or (other is not None and o != other):
                continue
            rows.append({"doc_id": d, "article": title(d),
                         "issue": f"{ARTICLES.magazine[d].title()} No. {ARTICLES.issue_no[d]}, "
                                  f"{ARTICLES.issue_date[d]}",
                         "pages": f"{ARTICLES.start_page[d]}–{ARTICLES.end_page[d]}",
                         "words": ARTICLES.word_count[d], f"topic {t}": r[t],
                         "other topic": tag(o), "other's share": ow})
    rows = pd.DataFrame(rows)
    _md(f"## Melds: articles with topic {tag(t)} and "
        f"{'topic ' + tag(other) if other is not None else 'another topic'}\n\n"
        f"Each at least {min_share:.0%} of the article; articles of {min_words}+ words; "
        f"{len(rows)} found. Use `article_boxes(doc_id)` to see where each topic falls.")
    if rows.empty:
        return
    _table(rows.sort_values("words", ascending=False).head(n))


def article_boxes(doc_id: str):
    """An article's text boxes in reading order: column, topic, words and the
    opening words of each box, so a meld can be checked by eye."""
    b = BOXES[BOXES.doc_id == doc_id].sort_values(["page", "reading_order", "chunk"])
    text = _box_text()
    _md(f"## {title(doc_id)}: {ARTICLES.word_count[doc_id]:,} words, box by box\n\n"
        "Mix: " + "; ".join(f"{tag(r.topic_id)} {r.weight:.0%}" for r in
                            ART_TOPICS[ART_TOPICS.doc_id == doc_id]
                            .sort_values("weight", ascending=False).itertuples()))
    _table(pd.DataFrame({"page": b.page, "column": b.column, "order": b.reading_order,
                         "topic": b.topic_id.map(tag), "words": b.words,
                         "similarity": b.similarity,
                         "opening words": [" ".join(text.get(i, "").split()[:12]) + "…"
                                           for i in b.box_id]}))


def page(volume: str, pg: int):
    """Any page's topics and its articles in reading order. volume and pg as in
    the page image's file name, e.g. saturday_1834_page_022 -> page("saturday_1834", 22)."""
    b = BOXES[(BOXES.volume == volume) & (BOXES.page == pg)]
    if b.empty:
        _md(f"## No modelled text on {volume} page {pg}.")
        return
    seq = int(ARTICLES.issue_seq[b.doc_id.iloc[0]])
    share = PAGES[(PAGES.volume == volume) & (PAGES.page == pg)].sort_values("share", ascending=False)
    _md(f"## {issue_name(volume, seq)}, page {pg}\n\n"
        "Page topics: " + "; ".join(f"{tag(r.topic_id)} {r.share:.0%} ({r.words:,.0f} words)"
                                    for r in share.itertuples()))
    _md("**The page in reading order** (runs of boxes of one article and one topic):")
    _table(_runs(b).drop(columns="page"))


def _runs(b: pd.DataFrame) -> pd.DataFrame:
    """Boxes in reading order, grouped into runs of one page, column, article and topic."""
    b = b.sort_values(["page", "reading_order", "chunk"])
    run_id = ((b.page != b.page.shift()) | (b.column != b.column.shift())
              | (b.doc_id != b.doc_id.shift()) | (b.topic_id != b.topic_id.shift())).cumsum()
    runs = (b.groupby(run_id).agg(page=("page", "first"), column=("column", "first"),
                                  doc_id=("doc_id", "first"), topic_id=("topic_id", "first"),
                                  words=("words", "sum"), boxes=("box_id", "count"))
             .reset_index(drop=True))
    return pd.DataFrame({"page": runs.page, "column": runs.column,
                         "article": runs.doc_id.map(title), "doc_id": runs.doc_id,
                         "topic": runs.topic_id.map(tag), "boxes": runs.boxes,
                         "words": runs.words})


def _issue_header(volume: str, issue_no: int):
    """The issue's articles, after printing its header and topic shares (None if not found)."""
    docs = ARTICLES[(ARTICLES.volume == volume) & (ARTICLES.issue_no.astype(str) == str(issue_no))]
    if docs.empty:
        _md(f"## No issue {issue_no} in {volume}.")
        return None
    seq = int(docs.issue_seq.iloc[0])
    share = ISSUES[(ISSUES.volume == volume) & (ISSUES.issue_seq == seq)].sort_values(
        "share", ascending=False)
    _md(f"## {issue_name(volume, seq)}: {len(docs)} articles, {int(share.words.sum()):,} words, "
        f"pages {docs.start_page.min()}–{docs.end_page.max()}\n\n"
        "Issue topics: " + "; ".join(f"{tag(r.topic_id)} {r.share:.0%} ({r.words:,.0f} words)"
                                     for r in share.itertuples()))
    return docs


def issue(volume: str, issue_no: int, min_weight: float = 0.05):
    """Any issue's articles in reading order, one row each, with their topics.
    issue_no is the printed number, e.g. issue("chambers_1843", 575).
    Other topics are listed when they hold at least min_weight of the article."""
    docs = _issue_header(volume, issue_no)
    if docs is None:
        return
    first = (BOXES[BOXES.doc_id.isin(docs.index)].sort_values(["page", "reading_order"])
             .groupby("doc_id").first())
    docs = docs.assign(_page=first.page.reindex(docs.index).fillna(docs.start_page),
                       _order=first.reading_order.reindex(docs.index).fillna(0),
                       column=first.column.reindex(docs.index).fillna(""))
    docs = docs.sort_values(["_page", "_order"])
    rows = []
    for d, a in docs.iterrows():
        mix = ART_TOPICS[(ART_TOPICS.doc_id == d) & (ART_TOPICS.weight >= min_weight)] \
            .sort_values("weight", ascending=False)
        others = mix[mix.topic_id != a.main_topic]
        rows.append({
            "pages": f"{a.start_page}" if a.start_page == a.end_page else f"{a.start_page}–{a.end_page}",
            "starts in": a.column, "article": title(d), "doc_id": d, "words": a.word_count,
            "main topic": tag(int(a.main_topic)) if a.modelled else "(not modelled)",
            "main share": a.main_weight if a.modelled else None,
            "other topics": "; ".join(f"{tag(r.topic_id)} {r.weight:.0%}" for r in others.itertuples()),
            "mix": "single topic" if others.empty else "meld",
            "series": " ".join(x for x in [a.series, a.series_part] if isinstance(x, str) and x),
            "boxes": a.n_boxes,
            "flags": ", ".join(f for f, on in [("short", a.short), ("US reprint", a.us_reprint),
                                               ("supplement", a.supplement)] if on == 1)})
    _md(f"**Articles in reading order** (other topics listed at {min_weight:.0%} or more of the "
        "article; `issue_boxes()` shows the same issue box by box):")
    _table(pd.DataFrame(rows))


def issue_boxes(volume: str, issue_no: int):
    """Any issue's boxes in reading order, page by page: runs of boxes of one
    page, column, article and topic. e.g. issue_boxes("chambers_1843", 575)."""
    docs = _issue_header(volume, issue_no)
    if docs is None:
        return
    _md("**The issue in reading order** (runs of boxes of one page, column, article and topic):")
    _table(_runs(BOXES[BOXES.doc_id.isin(docs.index)]))


_box_cache = {}


def _box_text():
    if not _box_cache:
        bc = pd.read_csv(CORPUS.parent / "boxes_corpus.csv", keep_default_na=False)
        _box_cache.update(zip(bc.box_id, bc.text))
    return _box_cache


def explore(t: int):
    overview(t)
    strongest_issue(t)
    strongest_page(t)
    partners(t)
