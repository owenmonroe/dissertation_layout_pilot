# Topic modelling

Topic models of the extracted articles, made two ways from the same body
text:

- **LDA** (gensim) reads whole articles. Each article gets a mix of topics.
- **BERTopic** reads text boxes. Each box (or piece of a long box) gets one
  topic, and each article's mix is its boxes' topics weighted by their words.

The input is a frozen extraction (`output/article_extraction/v6/articles.sqlite`).
Decisions and results are in
`documentation/topic_modelling/topic_modelling_decisions.md`.

## Environment

Run everything in the conda environment `topicmodel-env`. It is separate from
base Anaconda because BERTopic needs NumPy 2, which breaks base's pandas.

```
conda activate topicmodel-env      # or call ~/anaconda3/envs/topicmodel-env/bin/python
# made with: conda create -n topicmodel-env python=3.11
#            pip install bertopic sentence-transformers umap-learn hdbscan gensim pandas matplotlib ipykernel nbconvert
```

## Running

```
# 1. the corpus: articles and text boxes from the frozen extraction
python pipeline/topic_modelling/prepare_corpus.py --extraction v6

# 2. try topic counts 5-40 (config.SWEEP_KS), three seeds each
python pipeline/topic_modelling/run_topic_models.py --model lda --sweep
python pipeline/topic_modelling/run_topic_models.py --model bertopic --sweep
python pipeline/topic_modelling/run_topic_models.py --model lda --ks 12,14,16   # a finer range

# 3. choose the count: evaluation/topic_modelling/choose_k.ipynb

# 4. the final run at the chosen count
python pipeline/topic_modelling/run_topic_models.py --model lda --k 15
python pipeline/topic_modelling/run_topic_models.py --model bertopic --k 15
```

Every setting is in `config.py`.

## Code

| File | What it does |
|---|---|
| `config.py` | paths, filters, stop words, chunk size, model settings, sweep range |
| `prepare_corpus.py` | the corpus (articles + boxes), tokenising |
| `lda_model.py` | LDA fit, article mixes, top words |
| `bertopic_model.py` | box embeddings (cached), BERTopic fit with k-means, box topics, article mixes |
| `common.py` | scores (coherence, diversity, stability), topic tables, the issue/page/column tables, run info |
| `run_topic_models.py` | sweeps and final runs |

## Output: `output/topic_models/<extraction>/`

**`corpus/`**
- `articles_corpus.csv`: one row per article, with metadata, flags and body
  text. The flags are `short` (under 50 words), `empty` (no body) and
  `us_reprint` (Chambers 1840).
- `boxes_corpus.csv`: one row per text box or piece, with page, column,
  reading order and text.
- `corpus_info.json`: counts and settings.
- `embeddings_*.npy`: BERTopic's box embeddings (git-ignored).

**`sweeps/<model>/`**
- `sweep_scores.csv`: the scores of every run (topic count × seed).
- `sweep_summary.csv`: the mean and standard deviation of each score at
  each count, plus stability.
- `topics_k<N>.csv`: each topic's top words, number of articles, share of
  words and top articles, at that count.
- `sweeps/sweep_scores.png`: both models' scores against the topic count.

**`<model>_k<N>/`**: a final run.

`topics.sqlite` holds these tables (each also saved as a CSV):

| Table | One row per | What it holds |
|---|---|---|
| `topics` | topic | top words, word weights, `label` (empty, to fill in), articles mainly about it, share of all words, top articles, boxes (BERTopic) |
| `article_topics` | article × topic (weight ≥ 0.01) | weight, `is_main` |
| `articles` | article | extraction metadata (magazine, volume, issue number and date, title, series, pages, word count, flags), `main_topic`, `main_weight`, `modelled` |
| `box_topics` | text box or piece (BERTopic only) | page, column, reading order, words, topic, similarity to the topic's centre |
| `issue_topics` | issue × topic | words and share of the issue's body text |
| `page_topics` | page × topic | words and share of the page's body text |
| `column_topics` | column × topic | words and share of the column's body text |
| `topic_pairs_issue` | pair of topics | issues where both appear (each ≥ 10% of the words), issues with each, lift (above 1 = together more than chance) |
| `topic_pairs_page` | pair of topics | the same, for pages |

How the share tables get their words:
- **LDA:** each box's words are split across topics by its article's mix.
- **BERTopic:** each box's words all go to its own topic.

Also in each final run folder:
- `run_info.json`: model, topic count, seed, scores, package versions, git
  commit and corpus counts.
- `model/`: the saved model (git-ignored).
