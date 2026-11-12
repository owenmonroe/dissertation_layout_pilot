# Topic Modelling — Pilot Decisions

Experimental topic models of the articles extracted by frozen v6
(`extraction-v6`). The aim:
- choose a method and a topic count;
- build the setup that links each topic to its issue, page and column;
- rerun all of it on the full corpus once every volume is extracted.

Code: `pipeline/topic_modelling/` (see its `README.md` to run it). Choosing
the count: `evaluation/topic_modelling/choose_k.ipynb`. Output:
`output/topic_models/v6/`. Built 2026-11-11.

**This is a pilot.** The corpus is 15 volumes × 3 issues. The 16 topics
describe this sample. A full-corpus run will find its own count and its own
topics.

---

## 1. The corpus

**Decision** (Owen, 2026-11-11):
- **Source:** frozen v6's `articles.sqlite`, all 15 volumes run so far (555
  items).
- **Editorial notices are left out** (5).
- **Body text only:** no front or back matter (sources, bylines, notes), no
  tables, no captions.
- **Short pieces are kept** (34 under 50 words), flagged `short`, to filter at
  analysis time if wanted.
- **Chambers 1840 is kept,** flagged `us_reprint` (43 articles), until the
  edition question is decided.

**Result:** 550 articles and 586,445 words. Each article's word count matches
the extraction exactly, since its body is the body of its text boxes.

**Two articles have no topic.** Both are extraction faults:
- Saturday 1832's `saturday_0012` has no body;
- `saturday_1843_0001` has only masthead OCR.

They stay in the tables with `modelled = 0`.

**Words.** Each text is tokenised as follows:
- letters only, at least 3 long, lowercased;
- a line-end hyphen left before a space is rejoined ("per- ceived");
- English stop words plus older function words (`config.EXTRA_STOPWORDS`)
  are left out;
- the vocabulary keeps words found in at least 3 articles and no more than
  half of them.

There is no lemmatising.

## 2. Two models, from the same text

**Decision:** run both models and compare them.
- **LDA** (gensim) reads each article whole. A bag of words has no length
  limit.
- **BERTopic** embeds text, and its embedding model (all-mpnet-base-v2)
  reads at most 384 word pieces, about 280 words. Articles average 1,058
  words, and 298 of the 550 are over 512 words, so an article read whole
  would be judged on its opening.

  BERTopic therefore reads the article's **text boxes**, which the extraction
  already made:
  - 4,370 boxes, with a median of 114 words;
  - a box over 300 words is cut into even pieces of about 200 (404 boxes,
    giving 4,898 pieces).

  Each box gets one topic. Its **article's mix** is its boxes' topics,
  weighted by their words.
- **Clustering is k-means**, so the topic count is set, as for LDA. Every
  box gets a topic, with no outliers.
- **Topic words:** BERTopic gets each box as the same word list LDA uses, so
  both draw their topic words from one vocabulary. BERTopic's own cleaning
  strips hyphens and apostrophes ("stage-coaches" → "stagecoaches"), which
  lost words and broke its word weighting.

## 3. Choosing the count

**Method:** each count was run with three seeds:
- 5–40 in steps of 5 for both models;
- 12–24 in steps of 2, plus 17, for BERTopic.

Each run was scored on:
- **coherence** (c_v and NPMI: how often a topic's top words occur together
  in the articles);
- **diversity** (the share of distinct words in all topics' top 25);
- **stability** (how alike the topics of the three seeds are).

The scores narrow the range. The choice comes from reading each topic's
words and top articles.

**LDA was set aside** (Owen, 2026-11-11). At every count it scored below
BERTopic:

| | LDA | BERTopic |
|---|---|---|
| c_v | 0.39–0.43 | 0.51–0.59 |
| Diversity | 0.59–0.70 | 0.95–0.97 |
| Stability | 0.22–0.41 | 0.56–0.95 |

Its topics were led by general narrative words (man, day, like, old, good),
and a new seed gave largely new topics. A tighter vocabulary (no more than
25% of articles instead of 50%) might help. It is untried and left for
later.

**BERTopic, 12–24 topics:**

| Topics | c_v | Stability | Reading the topics |
|---|---|---|---|
| 12–14 | 0.53–0.55 | 0.59–0.62 | coarse: plants and animals one topic, plague with sea voyages |
| **16** | **0.53 (sd 0.003)** | **0.67** | every topic one nameable subject |
| 17 | 0.52 | 0.63 | adds patents, heat and metals, Egyptian antiquities; mixes mythology with Christmas |
| 18–20 | 0.53 | 0.57–0.63 | adds a working-class labour topic; some topics mix again |
| 22–24 | 0.52 | 0.62–0.65 | single articles become topics |

Coherence falls slowly as the count rises, with no clear peak, as is usual
for a corpus this small.

**Decision** (Owen, 2026-11-11): **16 topics.** At 16:
- every topic names one subject;
- the three seeds gave almost the same topics.

**Noted:** 20 topics gives a topic on labour and the working classes, which
interests Owen. The full-corpus run, with more text, should be able to
support topics this fine.

**Small, clear topics are kept.** Chess, archery, Christmas and mythology are
not central to the research, but they are sharp, coherent topics (Owen).
BERTopic sorts boxes, so one long article can make its own topic when
nothing else is like it. Archery is one: 2 articles, 1% of the words.

## 4. The final run: BERTopic, 16 topics

`output/topic_models/v6/bertopic_k16/`: seed 1, c_v 0.53, diversity 0.97.
548 of 550 articles modelled.

| Topic | Subject (suggested name) | Articles mainly on it | Share of words |
|---|---|---|---|
| 0 | Tales and domestic fiction | 95 | 17.6% |
| 1 | Population, public improvements, education | 68 | 13.9% |
| 2 | Knowledge, books and self-improvement | 103 | 10.0% |
| 3 | Towers, kings and earls (history, buildings) | 37 | 9.3% |
| 4 | Ballads, songs and Christmas | 50 | 5.9% |
| 5 | Ice, timber and glaciers | 34 | 7.5% |
| 6 | Sea voyages and islands | 32 | 6.5% |
| 7 | Art and engraving | 16 | 5.4% |
| 8 | Plants and insects | 23 | 5.0% |
| 9 | Animals | 36 | 5.5% |
| 10 | Shipping and Trinity House | 15 | 3.4% |
| 11 | French aristocratic tales | 13 | 4.1% |
| 12 | Mythology | 7 | 2.7% |
| 13 | Plague and quack medicine | 11 | 2.3% |
| 14 | Chess problems | 6 | 0.3% |
| 15 | Archery | 2 | 0.6% |

The names are suggestions. The `label` column in `topics` is left for Owen.

**Output tables** (`topics.sqlite`, each also a CSV):
- `topics`, `article_topics`, `articles`, `box_topics`;
- `issue_topics`, `page_topics`, `column_topics`: each topic's share of the
  body text in each issue, page and column;
- `topic_pairs_issue`, `topic_pairs_page`: pairs of topics that each hold at
  least 10% of an issue's (or page's) words, with a lift above 1 when they
  appear together more often than chance.

## 5. Known limits

- **Pilot sample:** 45 issues. The topic count and topics will change on the
  full corpus.
- **Extraction errors carry through:**
  - The Chambers 1840 imprint ("NEW YORK: Printed and published by…") is an
    article, and it shows among a topic's top articles.
  - Articles split or merged by the extraction get their topics as split or
    merged.
- **OCR noise:** some appears among topic words (the chess notation "chg").
- **No lemmatising:** "animal" and "animals" are separate words.
- **The American reprint** is in the corpus, flagged, until the edition
  question is decided.

## Next

1. Label the 16 topics (`topics.label`).
2. Explore co-occurrence by issue, page and column (a notebook on
   `topics.sqlite`).
3. On the full corpus: rebuild the corpus and sweep again. LDA could be
   tried again there with a tighter vocabulary.
