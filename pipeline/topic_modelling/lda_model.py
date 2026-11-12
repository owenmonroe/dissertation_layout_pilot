"""LDA (gensim) on whole articles: each article is one bag of words, any length."""
import numpy as np
from gensim.corpora import Dictionary
from gensim.models import LdaModel

import config as C


def dictionary(token_lists) -> Dictionary:
    """The shared vocabulary: words in at least NO_BELOW articles and no more
    than NO_ABOVE of them. BERTopic uses the same words for its topic words."""
    d = Dictionary(token_lists)
    d.filter_extremes(no_below=C.NO_BELOW, no_above=C.NO_ABOVE, keep_n=None)
    d.compactify()
    return d


def fit(k: int, seed: int, bows, d: Dictionary) -> LdaModel:
    return LdaModel(corpus=bows, id2word=d, num_topics=k, random_state=seed, **C.LDA)


def article_mix(model: LdaModel, bows) -> np.ndarray:
    """Topic weights per article (rows sum to 1; an article with no words in
    the vocabulary gets a row of zeros)."""
    mix = np.zeros((len(bows), model.num_topics))
    for i, bow in enumerate(bows):
        if not bow:
            continue
        for t, w in model.get_document_topics(bow, minimum_probability=0.0):
            mix[i, t] = w
    return mix


def top_words(model: LdaModel, n: int = C.TOP_WORDS) -> list[list[tuple[str, float]]]:
    return [[(w, float(p)) for w, p in model.show_topic(t, n)] for t in range(model.num_topics)]
