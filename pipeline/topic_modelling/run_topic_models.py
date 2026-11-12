"""Topic models on a frozen extraction's articles.

    # build the corpus (articles + text boxes) from output/article_extraction/v6
    python pipeline/topic_modelling/prepare_corpus.py --extraction v6

    # try a range of topic counts, three seeds each
    python pipeline/topic_modelling/run_topic_models.py --model lda --sweep
    python pipeline/topic_modelling/run_topic_models.py --model bertopic --sweep

    # the final run at the chosen count
    python pipeline/topic_modelling/run_topic_models.py --model lda --k 15

Run in the `topicmodel-env` conda environment. Output:
output/topic_models/<extraction>/sweeps/<model>/ and
output/topic_models/<extraction>/<model>_k<N>/ (see README.md).
"""
import argparse
import json

import numpy as np
import pandas as pd

import common
import config as C
import prepare_corpus


class Data:
    def __init__(self, extraction: str, need_embeddings: bool):
        self.extraction = extraction
        self.articles, self.boxes, self.info = prepare_corpus.load(extraction)
        self.corpus_dir = C.OUT_DIR / extraction / "corpus"
        self.tokens = [prepare_corpus.tokenize(t) for t in self.articles.text]
        import lda_model
        self.dictionary = lda_model.dictionary(self.tokens)
        self.bows = [self.dictionary.doc2bow(t) for t in self.tokens]
        self.embeddings = None
        if need_embeddings:
            import bertopic_model
            self.embeddings = bertopic_model.embed(self.boxes, self.corpus_dir)


def fit(model: str, k: int, seed: int, data: Data):
    """Fit one model; return (topic words, article mix, extra results)."""
    if model == "lda":
        import lda_model
        m = lda_model.fit(k, seed, data.bows, data.dictionary)
        return lda_model.top_words(m), lda_model.article_mix(m, data.bows), dict(model=m)
    import bertopic_model
    m = bertopic_model.fit(k, seed, data.boxes.text, data.embeddings,
                           data.dictionary.token2id.keys())
    topics, sim = bertopic_model.box_topics(m, data.embeddings)
    mix = bertopic_model.article_mix(data.boxes.doc_id, topics, data.boxes.words,
                                     list(data.articles.doc_id), k)
    return bertopic_model.top_words(m, k), mix, dict(model=m, box_topics=topics, similarity=sim)


def sweep(model: str, ks, seeds, data: Data):
    out = C.OUT_DIR / data.extraction / "sweeps" / model
    out.mkdir(parents=True, exist_ok=True)
    rows, words_by_k = [], {}
    for k in ks:
        for seed in seeds:
            words, mix, _ = fit(model, k, seed, data)
            scores = common.coherence(words, data.tokens, data.dictionary)
            rows.append(dict(model=model, k=k, seed=seed, **scores,
                             diversity=common.diversity(words)))
            words_by_k.setdefault(k, []).append(words)
            if seed == seeds[0]:
                common.topic_table(words, mix, data.articles).to_csv(out / f"topics_k{k}.csv", index=False)
            print(f"{model} k={k} seed={seed}: c_v {scores['c_v']:.3f}  "
                  f"npmi {scores['c_npmi']:.3f}  diversity {rows[-1]['diversity']:.2f}", flush=True)
    scores = pd.DataFrame(rows)
    # Add to earlier sweeps of this model; a rerun (k, seed) replaces the old row.
    if (out / "sweep_scores.csv").exists():
        old = pd.read_csv(out / "sweep_scores.csv")
        old = old[~old.set_index(["k", "seed"]).index.isin(scores.set_index(["k", "seed"]).index)]
        scores = pd.concat([old, scores]).sort_values(["k", "seed"])
    scores.to_csv(out / "sweep_scores.csv", index=False)
    summary = scores.groupby(["model", "k"]).agg(
        c_v=("c_v", "mean"), c_v_sd=("c_v", "std"), c_npmi=("c_npmi", "mean"),
        c_npmi_sd=("c_npmi", "std"), diversity=("diversity", "mean"),
        diversity_sd=("diversity", "std")).reset_index()
    earlier = (pd.read_csv(out / "sweep_summary.csv").set_index("k").stability
               if (out / "sweep_summary.csv").exists() else pd.Series(dtype=float))
    summary["stability"] = summary.k.map(
        lambda k: common.stability(words_by_k[k]) if k in words_by_k else earlier.get(k))
    summary.round(4).to_csv(out / "sweep_summary.csv", index=False)
    (out / "sweep_info.json").write_text(json.dumps(common.run_info(
        model, list(ks), list(seeds), data.extraction, data.info), indent=2, default=str))
    plot_sweeps(C.OUT_DIR / data.extraction / "sweeps")
    print(summary.round(3).to_string(index=False))


def plot_sweeps(sweeps_dir):
    """Small multiples, one panel per score, a line per model (both models'
    sweeps when both exist). Saved as sweeps/sweep_scores.png."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    frames = [pd.read_csv(p) for p in sorted(sweeps_dir.glob("*/sweep_summary.csv"))]
    if not frames:
        return
    s = pd.concat(frames)
    colours = {"lda": "#2a78d6", "bertopic": "#eb6834"}   # categorical slots 1, 2
    names = {"lda": "LDA (articles)", "bertopic": "BERTopic (text boxes)"}
    panels = [("c_v", "Coherence (c_v)"), ("c_npmi", "Coherence (NPMI)"),
              ("diversity", "Topic diversity"), ("stability", "Stability across seeds")]
    ink, muted, grid = "#2b2b29", "#6b6a64", "#e4e3de"
    fig, axes = plt.subplots(2, 2, figsize=(10, 7), sharex=True, facecolor="#fcfcfb")
    for ax, (col, title) in zip(axes.flat, panels):
        ax.set_facecolor("#fcfcfb")
        for m, g in s.groupby("model"):
            g = g.sort_values("k")
            ax.plot(g.k, g[col], color=colours.get(m), lw=2, marker="o", ms=6,
                    mec="#fcfcfb", mew=1.5, label=names.get(m, m))
            if f"{col}_sd" in g:
                ax.fill_between(g.k, g[col] - g[f"{col}_sd"], g[col] + g[f"{col}_sd"],
                                color=colours.get(m), alpha=0.12, lw=0)
            last = g.iloc[-1]
            ax.annotate(names.get(m, m).split(" ")[0], (last.k, last[col]), xytext=(6, 0),
                        textcoords="offset points", va="center", fontsize=8, color=ink)
        ax.set_title(title, loc="left", fontsize=10, color=ink)
        ax.grid(axis="y", color=grid, lw=0.8)
        ax.tick_params(colors=muted, labelsize=8, length=0)
        for side in ("top", "right", "left"):
            ax.spines[side].set_visible(False)
        ax.spines["bottom"].set_color(grid)
    for ax in axes[1]:
        ax.set_xlabel("Number of topics (k)", fontsize=9, color=muted)
    axes[0, 0].legend(frameon=False, fontsize=8, labelcolor=ink)
    fig.suptitle("Topic-count sweep: mean of three seeds (band = ±1 sd)",
                 x=0.06, ha="left", fontsize=11, color=ink)
    fig.tight_layout()
    fig.savefig(sweeps_dir / "sweep_scores.png", dpi=150, facecolor="#fcfcfb")
    plt.close(fig)


def final(model: str, k: int, seed: int, data: Data):
    words, mix, extra = fit(model, k, seed, data)
    a = data.articles
    has = mix.sum(axis=1) > 0
    main = np.where(has, mix.argmax(axis=1), -1)

    topics = common.topic_table(words, mix, a)
    topics.insert(1, "label", "")
    topics.insert(3, "word_weights", [json.dumps([[w, round(p, 5)] for w, p in t]) for t in words])
    topics["n_boxes"] = (np.bincount(extra["box_topics"], minlength=k)
                         if model == "bertopic" else None)

    rows = []
    for i, d in enumerate(a.doc_id):
        for t in np.flatnonzero(mix[i] >= 0.01):
            rows.append(dict(doc_id=d, volume=a.volume.iat[i], article_id=a.article_id.iat[i],
                             topic_id=int(t), weight=round(float(mix[i, t]), 4),
                             is_main=bool(t == main[i])))
    article_topics = pd.DataFrame(rows)

    articles = a.drop(columns=["text"]).assign(
        main_topic=np.where(has, main, None),
        main_weight=np.where(has, mix.max(axis=1).round(4), None),
        modelled=has)

    tables = dict(topics=topics, article_topics=article_topics, articles=articles)
    if model == "bertopic":
        bt = data.boxes.drop(columns=["text"]).assign(
            topic_id=extra["box_topics"], similarity=extra["similarity"].round(4))
        tables["box_topics"] = bt
        units = common.unit_weights(data.boxes, a, box_topic=extra["box_topics"])
    else:
        units = common.unit_weights(data.boxes, a, mix=mix)

    issue_keys = ["volume", "magazine", "issue_seq", "issue_no", "issue_date"]
    tables["issue_topics"] = common.shares(units, issue_keys)
    tables["page_topics"] = common.shares(units, ["volume", "issue_seq", "page"])
    tables["column_topics"] = common.shares(units, ["volume", "issue_seq", "page", "column"])
    tables["topic_pairs_issue"] = common.pairs(tables["issue_topics"], issue_keys)
    tables["topic_pairs_page"] = common.pairs(tables["page_topics"], ["volume", "issue_seq", "page"])

    out = C.OUT_DIR / data.extraction / f"{model}_k{k}"
    scores = dict(**common.coherence(words, data.tokens, data.dictionary),
                  diversity=common.diversity(words))
    info = common.run_info(model, k, seed, data.extraction, data.info, dict(scores=scores))
    common.write_final(out, tables, info)
    model_dir = out / "model"
    model_dir.mkdir(exist_ok=True)
    if model == "lda":
        extra["model"].save(str(model_dir / "lda"))
    else:
        extra["model"].save(str(model_dir / "bertopic"), serialization="safetensors",
                            save_ctfidf=True, save_embedding_model=C.EMBEDDING_MODEL)
    print(f"{model} k={k}: {json.dumps({k2: round(v, 3) for k2, v in scores.items()})}")
    print(f"wrote {out.relative_to(C.ROOT)}: " + ", ".join(f"{n} ({len(t)})" for n, t in tables.items()))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--extraction", default=C.DEFAULT_EXTRACTION)
    p.add_argument("--model", choices=["lda", "bertopic"], required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--sweep", action="store_true", help="try the topic counts in config.SWEEP_KS")
    g.add_argument("--ks", help="try these topic counts, e.g. 8,10,12")
    g.add_argument("--k", type=int, help="the final run at this topic count")
    p.add_argument("--seeds", help="comma-separated seeds for a sweep (default config.SWEEP_SEEDS)")
    p.add_argument("--rebuild-corpus", action="store_true")
    a = p.parse_args()
    if a.rebuild_corpus:
        prepare_corpus.write(a.extraction)
    data = Data(a.extraction, need_embeddings=a.model == "bertopic")
    if a.k:
        final(a.model, a.k, C.FINAL_SEED, data)
    else:
        ks = C.SWEEP_KS if a.sweep else [int(x) for x in a.ks.split(",")]
        seeds = [int(x) for x in a.seeds.split(",")] if a.seeds else C.SWEEP_SEEDS
        sweep(a.model, ks, seeds, data)


if __name__ == "__main__":
    main()
