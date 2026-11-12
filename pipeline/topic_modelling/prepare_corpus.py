"""Build the topic-modelling corpus from a frozen extraction's articles.sqlite.

Two tables, written to output/topic_models/<extraction>/corpus/:
- articles_corpus.csv: one row per article (body text, metadata, flags);
- boxes_corpus.csv: one row per text box, or per piece of a long box, with
  its page, column and reading order.

An article's body is the body of its text boxes, in reading order (the same
text the extraction's `text` column holds; word counts match exactly).
"""
import json
import re
import sqlite3
import unicodedata

import pandas as pd
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

import config as C

STOPWORDS = frozenset(ENGLISH_STOP_WORDS) | frozenset(C.EXTRA_STOPWORDS)
TOKEN = re.compile(C.TOKEN_PATTERN)

ARTICLE_COLUMNS = [
    "volume", "article_id", "magazine", "issue_seq", "issue_no", "issue_date",
    "title", "article_type", "supplement", "series", "series_part", "part",
    "continues_article_id", "continued_by_article_id", "index_group",
    "start_page", "end_page", "pages", "page_columns", "word_count",
]


def normalise(text: str) -> str:
    """Spellings the OCR or the press made that shouldn't split a word."""
    text = unicodedata.normalize("NFKC", text or "")  # ligatures (ﬁ, ﬂ)
    text = text.replace("ſ", "s").replace("’", "'").replace("‘", "'")
    # A hyphen at a line end, left with a space after it ("per- ceived"): the
    # next part starts lowercase. A hyphen with no space is a compound.
    text = re.sub(r"([A-Za-z])-\s+([a-z])", r"\1\2", text)
    return text.lower()


def tokenize(text: str) -> list[str]:
    words = (w.strip("'") for w in TOKEN.findall(normalise(text)))
    words = (w[:-2] if w.endswith("'s") else w for w in words)
    return [w for w in words if len(w) >= C.MIN_TOKEN_LEN and w not in STOPWORDS
            and "'" not in w]


def box_body(r) -> str:
    """The box's text without its front or back matter (layout.Region.body)."""
    body = r.text or ""
    if r.front_text and body.startswith(r.front_text):
        body = body[len(r.front_text):]
    if r.back_text and body.rstrip().endswith(r.back_text):
        body = body.rstrip()[:-len(r.back_text)]
    return body.strip().rstrip("—–- ").strip()


def chunks(text: str) -> list[str]:
    """A box over CHUNK_MAX words, cut into even pieces of about CHUNK_TARGET."""
    words = text.split()
    if len(words) <= C.CHUNK_MAX:
        return [text]
    n = round(len(words) / C.CHUNK_TARGET)
    size = -(-len(words) // n)
    return [" ".join(words[i:i + size]) for i in range(0, len(words), size)]


def year_of(date: str):
    m = re.search(r"(\d{4})$", date or "")
    return int(m.group(1)) if m else None


def build(extraction: str):
    db = C.EXTRACTION_DIR / extraction / "articles.sqlite"
    con = sqlite3.connect(db)
    articles = pd.read_sql("SELECT * FROM articles", con)
    regions = pd.read_sql(
        "SELECT volume, article_id, region_id, page, column, reading_order, role, "
        "text, front_text, back_text FROM regions WHERE role = 'text' "
        "AND article_id IS NOT NULL AND article_id != ''", con)
    regions[["text", "front_text", "back_text", "column"]] = \
        regions[["text", "front_text", "back_text", "column"]].fillna("")
    con.close()

    n_all = len(articles)
    excluded = articles[articles.article_type.isin(C.EXCLUDE_TYPES)]
    articles = articles[~articles.article_type.isin(C.EXCLUDE_TYPES)].copy()
    articles["doc_id"] = articles.volume + "/" + articles.article_id
    articles["year"] = articles.issue_date.map(year_of)
    articles["us_reprint"] = articles.volume.isin(C.US_REPRINT_VOLUMES)
    articles["empty"] = articles.word_count == 0
    articles["short"] = (articles.word_count > 0) & (articles.word_count < C.SHORT_WORDS)

    # Boxes, in reading order within each article.
    regions = regions.merge(articles[["volume", "article_id", "doc_id"]],
                            on=["volume", "article_id"])
    regions["body"] = regions.apply(box_body, axis=1)
    regions = regions[regions.body.str.strip() != ""]
    regions = regions.sort_values(["volume", "article_id", "page", "reading_order"])
    rows = []
    for r in regions.itertuples():
        pieces = chunks(r.body)
        for i, piece in enumerate(pieces):
            rows.append(dict(
                box_id=f"{r.volume}/{r.region_id}" + (f"#{i + 1}" if len(pieces) > 1 else ""),
                doc_id=r.doc_id, volume=r.volume, article_id=r.article_id,
                region_id=r.region_id, chunk=i + 1, n_chunks=len(pieces),
                page=r.page, column=r.column or "", reading_order=r.reading_order,
                words=len(piece.split()), text=piece))
    boxes = pd.DataFrame(rows)

    body = boxes.groupby("doc_id").text.apply(lambda t: "\n\n".join(t))
    articles["text"] = articles.doc_id.map(body).fillna("")
    articles["n_boxes"] = articles.doc_id.map(boxes.groupby("doc_id").region_id.nunique()).fillna(0).astype(int)
    articles["n_tokens"] = articles.text.map(lambda t: len(tokenize(t)))
    boxes["n_tokens"] = boxes.text.map(lambda t: len(tokenize(t)))

    cols = ["doc_id"] + ARTICLE_COLUMNS + ["year", "us_reprint", "short", "empty",
                                           "n_boxes", "n_tokens", "text"]
    articles = articles[cols]
    info = dict(
        extraction=extraction, source=str(db.relative_to(C.ROOT)),
        articles_in_extraction=n_all,
        excluded={t: int((excluded.article_type == t).sum()) for t in C.EXCLUDE_TYPES},
        articles=len(articles), short=int(articles["short"].sum()),
        empty=int(articles["empty"].sum()),
        no_tokens_after_stopwords=int(((articles.n_tokens == 0) & ~articles["empty"]).sum()),
        us_reprint=int(articles.us_reprint.sum()),
        boxes=int(boxes.region_id.nunique()), box_pieces=len(boxes),
        boxes_split=int(boxes[boxes.n_chunks > 1].groupby(["volume", "region_id"]).ngroups),
        words=int(articles.word_count.sum()),
        settings=dict(short_words=C.SHORT_WORDS, us_reprint_volumes=sorted(C.US_REPRINT_VOLUMES),
                      chunk_max=C.CHUNK_MAX, chunk_target=C.CHUNK_TARGET,
                      token_pattern=C.TOKEN_PATTERN, min_token_len=C.MIN_TOKEN_LEN,
                      extra_stopwords=C.EXTRA_STOPWORDS),
    )
    return articles, boxes, info


def write(extraction: str):
    articles, boxes, info = build(extraction)
    out = C.OUT_DIR / extraction / "corpus"
    out.mkdir(parents=True, exist_ok=True)
    articles.to_csv(out / "articles_corpus.csv", index=False)
    boxes.to_csv(out / "boxes_corpus.csv", index=False)
    (out / "corpus_info.json").write_text(json.dumps(info, indent=2))
    return articles, boxes, info


def load(extraction: str):
    out = C.OUT_DIR / extraction / "corpus"
    if not (out / "articles_corpus.csv").exists():
        return write(extraction)
    articles = pd.read_csv(out / "articles_corpus.csv", keep_default_na=False,
                           dtype={"issue_no": str, "series_part": str, "part": str})
    boxes = pd.read_csv(out / "boxes_corpus.csv", keep_default_na=False)
    info = json.loads((out / "corpus_info.json").read_text())
    return articles, boxes, info


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--extraction", default=C.DEFAULT_EXTRACTION)
    a = p.parse_args()
    _, _, info = write(a.extraction)
    print(json.dumps({k: v for k, v in info.items() if k != "settings"}, indent=2))
