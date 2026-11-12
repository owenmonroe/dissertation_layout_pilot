# Topic Examples: a Walkthrough

Five questions put to the pilot topic model, each with one strong example:
- which tables answer it;
- how to get the answer from the CSVs or the SQLite;
- what the result shows.

The model is BERTopic with 16 topics, on 550 articles from 45 issues of the
*Penny Magazine*, the *Saturday Magazine* and *Chambers's Edinburgh Journal*,
1832–1844. The issues are listed in `../full_build_test_texts_sample.md`.

- **Data:** `output/topic_models/v6/bertopic_k16/`, with `topics.sqlite` and
  the same tables as CSVs.
- **Every number below** comes from `topic_examples.py`, run in the
  `topicmodel-env` environment:
  `python evaluation/topic_modelling/topic_examples.py`.

**This is a pilot.** With 45 issues, these examples show what the method can
find. They are not results about the magazines yet.

---

## The topics

The names are suggestions; the `label` column in `topics` is still empty.

| Topic | Subject | Topic | Subject |
|---|---|---|---|
| 0 | Tales and domestic fiction | 8 | Plants and insects |
| 1 | Population, public improvements, education | 9 | Animals |
| 2 | Knowledge, books and self-improvement | 10 | Shipping and Trinity House |
| 3 | Towers, kings and earls (history, buildings) | 11 | French aristocratic tales |
| 4 | Ballads, songs and Christmas | 12 | Mythology |
| 5 | Ice, timber and glaciers | 13 | Plague and quack medicine |
| 6 | Sea voyages and islands | 14 | Chess problems |
| 7 | Art and engraving | 15 | Archery |

## The tables, and how they connect

```
issue_topics / page_topics / column_topics      topic shares of an issue, page or column
        │  volume + issue_seq (+ page, column)
        ▼
articles                                          one row per article: title, issue, pages, main topic
        │  doc_id
        ▼
article_topics                                    one row per article per topic: its weight
        │  doc_id
        ▼
box_topics                                        one row per text box: page, column, reading order, topic
```

How the numbers are built:
- **Each text box gets one topic.**
- **An article's weight** for a topic is the share of its words in boxes
  with that topic.
- **An issue, page or column share** is the same, added up over all the boxes
  in it.

So every share means *the share of body-text words*.

---

## 1. The most prevalent topic across the three magazines

**Tables:** `issue_topics`, added up by `magazine`.

**Steps**
- *In Numbers:* open `issue_topics.csv` and make a pivot table:
  - rows: `magazine`;
  - columns: `topic_id`;
  - values: sum of `words`.

  Divide each cell by its row total.
- *In SQLite:*
  ```sql
  SELECT magazine, topic_id, SUM(words) AS words
  FROM issue_topics GROUP BY magazine, topic_id
  ORDER BY magazine, words DESC;
  ```

**Result: each magazine has a different leading topic.**

| Magazine | 1st | 2nd | 3rd |
|---|---|---|---|
| Chambers's | **0 Fiction**, 28.9% | 1 Population and improvement, 15.6% | 2 Knowledge and books, 11.0% |
| Penny | **3 Towers, kings, earls**, 17.5% | 1 Population and improvement, 14.8% | 5 Ice and timber, 11.6% |
| Saturday | **3 Towers, kings, earls**, 14.8% | 7 Art and engraving, 14.5% | 5 Ice and timber, 13.1% |

**Which topic leads "across the three" depends on how you count.**

| Topic | Share of all words | Each magazine counted equally |
|---|---|---|
| 0 Fiction | **17.6%** | 11.6% |
| 1 Population and improvement | 13.9% | **13.0%** |
| 3 Towers, kings, earls | 9.3% | 12.1% |

- **All words pooled:** fiction leads. But Chambers prints about 2.5 times
  as many words per issue as the others, and 82 of the 95 articles mainly
  on fiction are in Chambers.
- **Each magazine counted equally:** topic 1 (population, public improvements,
  education) leads. It is the most even across the three: 15.6% in
  Chambers's, 14.8% in Penny and 8.7% in Saturday.

**To present:** fiction is Chambers's signature. History and buildings lead
the Penny and the Saturday. Improvement and education is the subject common
to all three.

---

## 2. Where topic 9 (animals) is strongest, and what else is there

**Tables:** `issue_topics`, then `articles`, then `article_topics`.

**Steps**
1. **Find the issue:** in `issue_topics`, keep `topic_id = 9` and sort by
   `share`, largest first. The top issue is **Saturday 1832, No. 2
   (07-14-1832)**: topic 9 holds 2,910 words, **35%** of the issue.
2. **List its topics:** in `issue_topics`, keep that issue (`volume =
   saturday`, `issue_seq = 2`). Every topic in it is listed with its share.
3. **List its articles:** in `articles`, keep the same issue to get the
   articles' `doc_id`s.
4. **See each article's topics:** in `article_topics`, keep those `doc_id`s.
   `weight × word_count` gives each article's words in each topic.

**Result**

| Topic in the issue | Share | Articles carrying it |
|---|---|---|
| 9 Animals | 35% | Wild Sports of the East (p12), Travelling in Spain (p10), Humming Birds (p11) |
| 5 Ice and timber | 18% | The Great Salcey Oak (p9) |
| 2 Knowledge and books | 17% | Sir Isaac Newton (p13), Wickliffe's Chair (p16), two short untitled pieces (p11) |
| 1 Population and improvement | 16% | On Bread (p15) |
| 3 Towers, kings, earls | 12% | Saint Swithun's Day (p14) |

**Reading it:** three whole articles about animals make this issue's
"animal" character, alongside an oak, a biography of Newton, bread and a
saint's day. Most articles here are almost entirely one topic (weight above
0.9). Saint Swithun's Day mixes history (80%) with its weather rhyme (topic
4, 10%).

---

## 3. Where topic 13 (plague and quack medicine) is strongest, and what else is there

**Tables:** the same chain as task 2.

**Steps:** in `issue_topics`, keep `topic_id = 13` and sort by `share`. Then
follow the issue into `articles` and `article_topics`.

**Result:** **Penny 1838, No. 432 (12-29-1838)**. Topic 13 is **61%** of the
issue.

| Topic in the issue | Share | Article |
|---|---|---|
| 13 Plague and quack medicine | 61% | Quacks and Quack Medicines (p15), 1,820 words, 98% topic 13 |
| 11 French aristocratic tales | 23% | Le Comte Alexandre-Louis-Joseph de Laborde (p14), 62% topic 11 |
| 7 Art and engraving | 14% | the same Laborde article, 38% topic 7 |

**Reading it:**
- **The issue has two articles, so the whole picture is two topics' worth
  of reading.** A satirical piece on quack medicines faces a biography of a
  French count.
- **The biography is itself a mix,** of aristocratic life and art. Laborde
  is known for illustrated works on travel and antiquities, which is the
  likely source of the art topic.

**A caution: share depends on issue size.** No. 432 is a short issue (2,914
words; its monthly supplement follows). The issue with the *most* words on
topic 13 is Chambers 1832 No. 1, with "Plague. Cholera" at 5,594 words, but
that is 26% of a much longer issue.
- Use **`share`** to find where a topic dominates.
- Use **`words`** to find where there is most of it.

---

## 4. The page where topic 1 is strongest, and what else is on it

**Tables:** `page_topics`, then `box_topics` and `articles` for the articles
and columns.

**Choosing the page:** many pages are 100% topic 1, because one article fills
the page, so they have nothing else on them. To see topic 1 *beside* other
topics, keep the pages where topic 1 has a share below 1, then sort.

**Steps**
1. In `page_topics`, keep `topic_id = 1` and `share < 1`. Sort by `share`,
   then by `words`.
2. For a chosen page, keep its rows in `page_topics` to see all its topics.
3. In `box_topics`, keep the same `volume` and `page`, and join to `articles`
   on `doc_id` to name the articles and columns.

```sql
SELECT a.title, b.column, b.topic_id, SUM(b.words) AS words
FROM box_topics b JOIN articles a USING (doc_id)
WHERE b.volume = 'chambers_1839' AND b.page = 8
GROUP BY a.title, b.column, b.topic_id
ORDER BY MIN(b.reading_order), b.column;
```

**Result:** **Chambers's Edinburgh Journal, No. 414 (01-04-1840), page 8.**
Topic 1 is 77% of the page; topic 9 (animals) is 23%.

| Column | Article | Topic | Words |
|---|---|---|---|
| left | Living in Paris | 1 Population and improvement | 901 |
| middle | Living in Paris | 1 | 1,060 |
| right | Living in Paris (end) | 1 | 133 |
| right | Hybernation, or Winter Sleep of Animals | 9 Animals | 641 |

**Reading it:**
- **The two topics are two separate articles,** side by side in the right-hand
  column. An essay on living in Paris gives way to natural
  history.
- **This is the juxtaposition the column tables are built to find:** two
  topics meeting on a page because the editor placed two articles there, not
  because one article mixes them.
- **Pages strongly topic 1 but not entirely** are often of this kind. A second
  example is Chambers No. 273 (04-22-1837), p22: "Belgian Industry" and
  "Steam in Belgium" (topic 1, 68%) beside "Instinct and Reason" (topic 2,
  30%).

---

## 5. An article where topic 2 combines with another topic

**Tables:** `article_topics` to find mixed articles, then `box_topics` to see
where in the article each topic falls.

**Finding one:** in `article_topics`, keep the articles with:
- **topic 2 at 0.3–0.7,** so it is a real part of the article but not all of it;
- **another topic at 0.25 or more;**
- **at least 1,000 words,** since a long article makes a clearer example.

Three articles qualify.

**Result:** **"Adventures of Robin Day"** (*Chambers's*, American reprint,
No. 106, 01-11-1840, pp17–18, 3,047 words). It is a review of a novel by
Robert Montgomery Bird, quoting long passages.

| Topic | Weight | Words |
|---|---|---|
| 6 Sea voyages and islands | 0.60 | about 1,816 |
| 2 Knowledge, books and self-improvement | 0.34 | about 1,044 |
| 0 Fiction | 0.06 | about 187 |

**Where the topics fall** (`box_topics`, in reading order):

| Page and column | Topics of the boxes |
|---|---|
| p17 right | 6 6 6 6 |
| p18 left | 6 6 6 6 6 6 6 · 6 6 6 6 (one 3-word fragment is topic 2) |
| p18 middle | 6 6 6 6 6, then 2 0 2 2 2 |
| p18 right | 2 2 2 2 |

**Reading it:**
- **The article changes subject partway through, and the boxes show
  where.** The first half follows Robin as an infant shipwrecked on the New
  Jersey coast, then as a skipper's boy on a shallop: topic 6, sea voyages.
- **From the middle column of p18,** his patron puts him to school, and the
  review turns to the school and its republican experiment in educating boys:
  topic 2.
- **The article's 0.60 / 0.34 mix reflects a real change of subject,** not
  uncertainty.

**Two cautions**
- **This article is from the American reprint** of Chambers's (flagged
  `us_reprint`).
- **Not every mixed article is a true mix.** Another of the three,
  "Speculations on Words" (Chambers No. 416), is about word origins
  throughout. Its boxes on "wilderness" and "Sheerness" went to sea voyages,
  and those on "villain, clown, boor" to fiction. The model reacts to the
  words discussed.

  Always check a mixed article's boxes before treating the mix as two
  subjects.

---

## Things to remember when using these tables

- **Small numbers:** 45 issues. A pattern seen in three or four issues is a
  lead to check, not a finding.
- **Share against words:** `share` says what dominates an issue, page or
  column. `words` says how much there is. Short issues and supplements
  inflate share.
- **Chambers is longer:** it prints about 2.5 times the words per issue, so
  pooled totals lean towards Chambers. Compare magazines on shares within
  each one.
- **Tiny boxes:** fragments under 20 words get topics of their own, which
  are often weak. They barely move shares, but they add small stray entries.
- **Extraction errors carry through:** a wrongly split or merged article has
  its topics split or merged the same way.
