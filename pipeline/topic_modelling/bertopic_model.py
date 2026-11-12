"""BERTopic on text boxes (pieces of at most CHUNK_MAX words).

Each box gets one topic. An article's topic mix is its boxes' topics weighted
by their word counts. Clustering is k-means, so the number of topics is set,
as in LDA, and every box gets a topic (no outliers).
"""
import hashlib
import json

import numpy as np
from bertopic import BERTopic
from bertopic.vectorizers import ClassTfidfTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import CountVectorizer
from umap import UMAP

import config as C
from prepare_corpus import tokenize


def embed(boxes, out_dir):
    """Sentence embeddings of the box texts, cached by model and texts."""
    key = hashlib.sha1(("\n".join(boxes.box_id) + "\n".join(boxes.text)).encode()).hexdigest()[:12]
    name = C.EMBEDDING_MODEL.split("/")[-1]
    path = out_dir / f"embeddings_{name}.npy"
    meta = out_dir / f"embeddings_{name}.json"
    if path.exists() and meta.exists() and json.loads(meta.read_text()).get("key") == key:
        return np.load(path)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(C.EMBEDDING_MODEL)
    emb = model.encode(list(boxes.text), batch_size=32, show_progress_bar=True,
                       normalize_embeddings=True)
    np.save(path, emb)
    meta.write_text(json.dumps(dict(key=key, model=C.EMBEDDING_MODEL, n=len(boxes),
                                    max_seq_length=model.max_seq_length)))
    return emb


def fit(k: int, seed: int, texts, embeddings, vocabulary) -> BERTopic:
    # The embeddings come from the box texts (embed). For its topic words
    # BERTopic gets each box as our own tokens, the same words LDA sees: its
    # own cleaning would strip hyphens and apostrophes and lose words
    # ("stage-coaches" -> "stagecoaches"), and a word then found in no topic
    # gets an infinite weight.
    docs = [" ".join(tokenize(t)) for t in texts]
    present = {w for d in docs for w in d.split()}
    vectorizer = CountVectorizer(vocabulary=sorted(set(vocabulary) & present),
                                 analyzer=str.split, lowercase=False)
    model = BERTopic(
        umap_model=UMAP(random_state=seed, **C.UMAP),
        hdbscan_model=KMeans(n_clusters=k, random_state=seed, n_init=10),
        vectorizer_model=vectorizer,
        ctfidf_model=ClassTfidfTransformer(reduce_frequent_words=True),
        top_n_words=C.TOP_WORDS, calculate_probabilities=False, verbose=False)
    model.fit(docs, embeddings=embeddings)
    return model


def box_topics(model: BERTopic, embeddings) -> tuple[np.ndarray, np.ndarray]:
    """Each box's topic, and its cosine similarity to its topic's centre."""
    topics = np.array(model.topics_)
    sim = np.zeros(len(topics))
    for t in np.unique(topics):
        idx = topics == t
        centre = embeddings[idx].mean(axis=0)
        centre /= np.linalg.norm(centre) or 1
        sim[idx] = embeddings[idx] @ centre
    return topics, sim


def article_mix(doc_ids, topics, words, articles_doc_ids, k) -> np.ndarray:
    """Article topic shares: each box's words go to its topic."""
    row = {d: i for i, d in enumerate(articles_doc_ids)}
    mix = np.zeros((len(articles_doc_ids), k))
    for d, t, w in zip(doc_ids, topics, words):
        mix[row[d], t] += w
    total = mix.sum(axis=1, keepdims=True)
    return np.divide(mix, total, out=np.zeros_like(mix), where=total > 0)


def top_words(model: BERTopic, k: int) -> list[list[tuple[str, float]]]:
    out = []
    for t in range(k):
        words = model.get_topic(t) or []
        out.append([(w, float(s)) for w, s in words[:C.TOP_WORDS] if w])
    return out
