"""Settings for topic modelling (pipeline/topic_modelling/).

Every choice that changes the corpus or the models is here, so a run's
run_info.json records it and the decisions file can point to it.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EXTRACTION_DIR = ROOT / "output" / "article_extraction"
OUT_DIR = ROOT / "output" / "topic_models"

# Which frozen extraction the corpus comes from.
DEFAULT_EXTRACTION = "v6"

# --- What goes in -----------------------------------------------------------
# Article types left out (Owen, 2026-11-11): editorial notices.
EXCLUDE_TYPES = {"editorial_notice"}
# Short pieces stay in, flagged; filter them at analysis time if wanted.
SHORT_WORDS = 50
# Volumes that aren't the British edition (Owen, 2026-11-10: flag, decide later).
US_REPRINT_VOLUMES = {"chambers_1840"}
# Body text only: no front or back matter, no tables, no captions.

# --- Text boxes for BERTopic -------------------------------------------------
# The embedding model reads at most 384 word pieces (about 280 words), so a
# box longer than CHUNK_MAX words is cut into even pieces of about CHUNK_TARGET.
CHUNK_MAX = 300
CHUNK_TARGET = 200

# --- Words -------------------------------------------------------------------
# Tokens: letters only, at least 3 long, lowercased. No lemmatising (yet).
TOKEN_PATTERN = r"(?u)\b[a-z][a-z']+[a-z]\b"
MIN_TOKEN_LEN = 3
# On top of scikit-learn's English stop words: older function words, forms of
# address, numbers written out, and words common to every kind of article.
EXTRA_STOPWORDS = """
upon thee thou thy thine ye hath doth hast dost art shalt wilt unto whilst
amongst amidst thus therefore hence whence thence wherein whereby thereof
also yet though although however may might shall would could must ought
one two three four five six seven eight nine ten first second third
many much every several great little made make making says said say
mr mrs miss sir st dr esq viz etc
well even still now often ever never always soon long way
time times part parts thing things kind sort place without within
""".split()

# --- Vocabulary for both models ---------------------------------------------
NO_BELOW = 3        # a word must be in at least 3 articles
NO_ABOVE = 0.5      # and in no more than half of them

# --- Models ------------------------------------------------------------------
SWEEP_KS = list(range(5, 41, 5))   # topic counts tried by --sweep
SWEEP_SEEDS = [1, 2, 3]            # each count run with three seeds (stability)
FINAL_SEED = 1
TOP_WORDS = 15
TOP_ARTICLES = 5

LDA = dict(passes=20, iterations=400, alpha="auto", eta="auto", chunksize=2000)

EMBEDDING_MODEL = "sentence-transformers/all-mpnet-base-v2"
UMAP = dict(n_neighbors=15, n_components=5, min_dist=0.0, metric="cosine")

# A topic counts as present on a page or in an issue when it holds at least
# this share of the words there (for the topic-pair tables).
PRESENT_SHARE = 0.10
