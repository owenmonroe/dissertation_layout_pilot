"""Scores for comparing topic counts, and the output tables of a final run."""
import itertools
import json
import platform
import sqlite3
import subprocess
from datetime import date
from importlib.metadata import version

import numpy as np
import pandas as pd
from gensim.models.coherencemodel import CoherenceModel

import config as C

# --- Scores ------------------------------------------------------------------

def coherence(topic_words, texts, d) -> dict:
    """c_v and NPMI coherence of each topic's top 10 words, measured on the
    article texts (the same reference for both models)."""
    topics = [[w for w, _ in t[:10] if w in d.token2id] for t in topic_words]
    topics = [t for t in topics if len(t) >= 2]
    out = {}
    for measure in ("c_v", "c_npmi"):
        cm = CoherenceModel(topics=topics, texts=texts, dictionary=d,
                            coherence=measure, processes=1)
        out[measure] = float(cm.get_coherence())
    return out


def diversity(topic_words, n: int = 25) -> float:
    """Share of distinct words among all topics' top n words (1 = no overlap)."""
    words = [w for t in topic_words for w, _ in t[:n]]
    return len(set(words)) / len(words) if words else 0.0


def stability(runs_topic_words, n: int = 10) -> float:
    """How alike the topics of different seeds are: for each pair of seeds,
    each topic's best Jaccard match of its top n words in the other run,
    averaged. 1 = the same topics every time."""
    sets = [[{w for w, _ in t[:n]} for t in run] for run in runs_topic_words]
    scores = []
    for a, b in itertools.permutations(sets, 2):
        for s in a:
            scores.append(max(len(s & o) / len(s | o) for o in b) if b else 0)
    return float(np.mean(scores)) if scores else float("nan")


# --- Reading topics ------------------------------------------------------------

def article_label(row) -> str:
    title = row.title or " ".join(row.text.split()[:8]) + "…"
    return f"{row.volume} p{row.start_page}: {title}"


def topic_table(topic_words, mix, articles, n_articles: int = C.TOP_ARTICLES) -> pd.DataFrame:
    rows = []
    main = mix.argmax(axis=1)
    has = mix.sum(axis=1) > 0
    words_total = (mix * articles.word_count.to_numpy()[:, None]).sum()
    for t, words in enumerate(topic_words):
        # Top articles: the most words given to this topic (weight × length),
        # so a long article mostly on the topic ranks above a one-box piece.
        order = np.argsort(-(mix[:, t] * articles.word_count.to_numpy()))[:n_articles]
        rows.append(dict(
            topic_id=t,
            top_words=" ".join(w for w, _ in words),
            n_articles_main=int(((main == t) & has).sum()),
            share_of_words=round(float((mix[:, t] * articles.word_count).sum() / words_total), 4),
            top_articles=" || ".join(f"{article_label(articles.iloc[i])} ({mix[i, t]:.2f})"
                                     for i in order if mix[i, t] > 0)))
    return pd.DataFrame(rows)


# --- Final run tables -----------------------------------------------------------

def unit_weights(boxes, articles, mix=None, box_topic=None) -> pd.DataFrame:
    """Words per topic in each box piece. LDA: the article's mix times the
    box's words. BERTopic: all the box's words to its own topic."""
    meta = articles.set_index("doc_id")[["magazine", "issue_seq", "issue_no", "issue_date"]]
    b = boxes.join(meta, on="doc_id")
    if box_topic is not None:
        out = b.assign(topic_id=box_topic, words_in_topic=b.words.astype(float))
    else:
        row = {d: i for i, d in enumerate(articles.doc_id)}
        parts = []
        for t in range(mix.shape[1]):
            w = b.doc_id.map(lambda d: mix[row[d], t]) * b.words
            parts.append(b.assign(topic_id=t, words_in_topic=w))
        out = pd.concat(parts)
        out = out[out.words_in_topic > 0]
    return out


def shares(units, keys) -> pd.DataFrame:
    g = units.groupby(keys + ["topic_id"], dropna=False).words_in_topic.sum().rename("words").reset_index()
    g["share"] = g.words / g.groupby(keys, dropna=False).words.transform("sum")
    g["words"] = g.words.round(1)
    g["share"] = g.share.round(4)
    return g[g.words > 0].reset_index(drop=True)


def pairs(share_table, keys) -> pd.DataFrame:
    """For each pair of topics: in how many issues (or pages) both are present
    (each at least PRESENT_SHARE of the words), and the lift: together / what
    chance alone would give (above 1 = they appear together more than chance)."""
    present = share_table[share_table.share >= C.PRESENT_SHARE]
    units = present.groupby(keys, dropna=False).topic_id.apply(set)
    n = len(share_table.groupby(keys, dropna=False))
    count = present.topic_id.value_counts()
    together = {}
    for s in units:
        for a, b in itertools.combinations(sorted(s), 2):
            together[(a, b)] = together.get((a, b), 0) + 1
    topics = sorted(share_table.topic_id.unique())
    rows = []
    for a, b in itertools.combinations(topics, 2):
        na, nb, nab = int(count.get(a, 0)), int(count.get(b, 0)), together.get((a, b), 0)
        rows.append(dict(topic_a=a, topic_b=b, together=nab, present_a=na, present_b=nb,
                         units=n, lift=round(nab * n / (na * nb), 3) if na and nb else None))
    return pd.DataFrame(rows).sort_values(["together", "lift"], ascending=False)


def run_info(model: str, k: int, seed: int, extraction: str, corpus_info: dict, extra=None) -> dict:
    def git(*args):
        try:
            return subprocess.check_output(["git", *args], cwd=C.ROOT, text=True).strip()
        except Exception:
            return None
    pkgs = {p: _version(p) for p in ("gensim", "bertopic", "sentence-transformers",
                                     "umap-learn", "scikit-learn", "numpy", "pandas", "torch")}
    return dict(model=model, k=k, seed=seed, extraction=extraction, run_date=str(date.today()),
                git_commit=git("rev-parse", "HEAD"),
                uncommitted_changes=bool(git("status", "--porcelain", "pipeline/topic_modelling")),
                python=platform.python_version(), packages=pkgs,
                corpus={k: v for k, v in corpus_info.items() if k != "settings"},
                settings=dict(no_below=C.NO_BELOW, no_above=C.NO_ABOVE, lda=C.LDA,
                              embedding_model=C.EMBEDDING_MODEL, umap=C.UMAP,
                              present_share=C.PRESENT_SHARE, **corpus_info.get("settings", {})),
                **(extra or {}))


def _version(p):
    try:
        return version(p)
    except Exception:
        return None


def write_final(out_dir, tables: dict, info: dict):
    out_dir.mkdir(parents=True, exist_ok=True)
    db = out_dir / "topics.sqlite"
    if db.exists():
        db.unlink()
    con = sqlite3.connect(db)
    for name, df in tables.items():
        df.to_sql(name, con, index=False)
        df.to_csv(out_dir / f"{name}.csv", index=False)
    con.close()
    (out_dir / "run_info.json").write_text(json.dumps(info, indent=2, default=str))
