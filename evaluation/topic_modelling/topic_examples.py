"""The five worked examples in topic_examples_walkthrough.md, from the final
BERTopic run (output/topic_models/v6/bertopic_k16/topics.sqlite).

    python evaluation/topic_modelling/topic_examples.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DB = ROOT / "output/topic_models/v6/bertopic_k16/topics.sqlite"
pd.set_option("display.width", 200)
pd.set_option("display.max_colwidth", 45)
con = sqlite3.connect(DB)


def show(title, sql):
    print(f"\n== {title}")
    print(pd.read_sql(sql, con).to_string(index=False))


# 1. Most prevalent topic in each magazine: issue_topics added up by magazine.
m = pd.read_sql("SELECT magazine, topic_id, SUM(words) AS words FROM issue_topics "
                "GROUP BY magazine, topic_id", con)
m["share"] = (m.words / m.groupby("magazine").words.transform("sum")).round(3)
print("\n== 1. Top topics in each magazine (share of the magazine's words)")
print(m.sort_values(["magazine", "share"], ascending=[True, False])
      .groupby("magazine").head(3).to_string(index=False))
print("\n== 1. All words together, and each magazine counted equally")
overall = m.groupby("topic_id").words.sum()
print(pd.DataFrame({"all_words_share": (overall / overall.sum()).round(3),
                    "magazines_equal_share": m.groupby("topic_id").share.mean().round(3)})
      .sort_values("magazines_equal_share", ascending=False).head(4).to_string())
show("1. Articles mainly on topic 0, by magazine",
     "SELECT magazine, COUNT(*) AS articles FROM articles WHERE main_topic = 0 GROUP BY magazine")

# 2. Issue where topic 9 is strongest, its other topics, and the articles.
show("2. Issues where topic 9 is strongest",
     "SELECT volume, issue_seq, issue_no, issue_date, words, share FROM issue_topics "
     "WHERE topic_id = 9 ORDER BY share DESC LIMIT 3")
show("2. All topics in Saturday 1832 No. 2",
     "SELECT topic_id, words, share FROM issue_topics "
     "WHERE volume = 'saturday' AND issue_seq = 2 ORDER BY share DESC")
show("2. Its articles and their topics",
     "SELECT a.title, a.start_page, t.topic_id, t.weight, ROUND(t.weight * a.word_count) AS topic_words "
     "FROM articles a JOIN article_topics t USING (doc_id) "
     "WHERE a.volume = 'saturday' AND a.issue_seq = 2 AND t.weight >= 0.05 "
     "ORDER BY t.topic_id, topic_words DESC")

# 3. Issue where topic 13 is strongest.
show("3. Issues where topic 13 is strongest",
     "SELECT volume, issue_seq, issue_no, issue_date, words, share FROM issue_topics "
     "WHERE topic_id = 13 ORDER BY share DESC LIMIT 3")
show("3. All topics in Penny 1838 No. 432",
     "SELECT topic_id, words, share FROM issue_topics "
     "WHERE volume = 'penny_1838' AND issue_seq = 2 ORDER BY share DESC")
show("3. Its articles and their topics",
     "SELECT a.title, a.start_page, a.word_count, t.topic_id, t.weight "
     "FROM articles a JOIN article_topics t USING (doc_id) "
     "WHERE a.volume = 'penny_1838' AND a.issue_seq = 2 ORDER BY a.start_page, t.weight DESC")

# 4. Page where topic 1 is strongest while sharing the page with another topic.
show("4. Pages mostly topic 1 that also hold another topic",
     "SELECT volume, issue_seq, page, words, share FROM page_topics "
     "WHERE topic_id = 1 AND share < 1 ORDER BY share DESC, words DESC LIMIT 5")
show("4. Chambers No. 414, p8: topics",
     "SELECT topic_id, words, share FROM page_topics "
     "WHERE volume = 'chambers_1839' AND issue_seq = 1 AND page = 8 ORDER BY share DESC")
show("4. Chambers No. 414, p8: articles, columns and topics",
     "SELECT a.title, b.column, b.topic_id, SUM(b.words) AS words "
     "FROM box_topics b JOIN articles a USING (doc_id) "
     "WHERE b.volume = 'chambers_1839' AND b.page = 8 "
     "GROUP BY a.title, b.column, b.topic_id ORDER BY MIN(b.reading_order), b.column")

# 5. An article where topic 2 combines with another topic.
show("5. Long articles: topic 2 between 0.3 and 0.7, another topic at least 0.25",
     """SELECT a.doc_id, a.title, a.word_count, t2.weight AS topic_2,
               o.topic_id AS other_topic, o.weight AS other_weight
        FROM articles a
        JOIN article_topics t2 ON t2.doc_id = a.doc_id AND t2.topic_id = 2
        JOIN article_topics o ON o.doc_id = a.doc_id AND o.topic_id != 2
        WHERE t2.weight BETWEEN 0.3 AND 0.7 AND o.weight >= 0.25 AND a.word_count >= 1000
        ORDER BY a.word_count DESC""")
show("5. 'Adventures of Robin Day': boxes in reading order",
     "SELECT page, column, reading_order, words, topic_id, similarity FROM box_topics "
     "WHERE doc_id = 'chambers_1840/chambers_1840_0018' ORDER BY page, reading_order")
