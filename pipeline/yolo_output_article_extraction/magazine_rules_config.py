"""Per-magazine settings.

Everything that differs between the magazines lives here; the pipeline code in
layout.py / text.py / articles.py is shared. Adding a magazine (or a new
volume layout) should mean adding an entry here, plus a new rule only if the
magazine does something the shared rules don't cover. Rules every magazine
uses (masthead dates and prices, run-in heads, attributions, bylines, ...) stay
in the shared code.

After changing anything here, run check_verified.py to make sure the pages
already checked by hand still come out the same.
"""

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Magazine:
    key: str
    columns: int
    # The magazine's name as printed in its masthead (in large type on an
    # issue's first page). Also used to drop a mid-issue "title" that is just
    # the name (a running head YOLO boxed as a title).
    name: re.Pattern
    # Masthead wording beyond the shared set (dates, prices, "No.", "PUBLISHED
    # EVERY SATURDAY", ...), used when reading down an issue's first page.
    masthead_words: re.Pattern
    # The publisher's imprint at the end of an issue: not an article.
    imprint: re.Pattern
    # Real items have run-in heads in capitals ("THE WASP."), so a mixed-case
    # run-in head ("The Bow.") or a run-in head inside a titled article
    # ("PLAGUE. CHOLERA" / "CLEANLINESS.—") is a subsection, not an item.
    run_in_capitals_only: bool = False
    # How this magazine prints its issue number (group 1 is the number); the
    # format can change between volumes, so list them all. Shared fallbacks
    # are in articles.py.
    issue_number: re.Pattern | None = None
    # Titles of this magazine's own editorial notices, beyond the shared
    # wording (notices, errata, addresses to readers): e.g. its publishing
    # body's notices. None: shared wording only.
    editorial: re.Pattern | None = None

    @property
    def column_names(self) -> list[str]:
        return ["left", "right"] if self.columns == 2 else ["left", "middle", "right"]


# Imprint wording shared by the London/Edinburgh publishers.
_IMPRINT = (r"^\W*(?:LONDON\s*:|PRINTED BY|PUBLISHED BY)|publisher'?s agents"
            r"|\bPrinters?, \d")  # "C. RICHARDS, Printer, 100, St. Martin's Lane"

MAGAZINES = {
    m.key: m for m in [
        Magazine(
            key="penny",
            columns=2,
            name=re.compile(r"penny\s+magazine", re.I),
            masthead_words=re.compile(r"society|knowledge", re.I),
            imprint=re.compile(_IMPRINT + r"|CHARLES KNIGHT|PALL[- ]MALL EAST", re.I),
            # "1.]", "271.]"; OCR reads the bracket as 3, 1, l or I ("270.3", "2.1").
            issue_number=re.compile(r"(?<![\d.,])(\d{1,4})\s*\.\s*[\]3lI1](?![\w])"),
        ),
        Magazine(
            key="saturday",
            columns=2,
            # Its masthead splits "Saturday" and "Magazine" around the seal.
            name=re.compile(r"^\W*(?:the\s+)?saturday\W*$|^\W*magazine\W*$", re.I),
            masthead_words=re.compile(r"saturday|society|committee|knowledge|one p[ae]nny", re.I),
            # "Nº 482.", "N°. 2.", "No. 483.", "№ 484."
            issue_number=re.compile(r"(?:\bN[oº°]|№)\s*\.?\s*(\d{1,4})\b"),
            imprint=re.compile(
                _IMPRINT + r"|^\W*JOHN WILLIAM PARKER|WEST STRAND", re.I),
            # The SPCK committee's notices to readers are articles (editorial
            # notices), not imprint.
            editorial=re.compile(r"COMMITTEE OF GENERAL LITERATURE", re.I),
        ),
        Magazine(
            key="chambers",
            columns=3,
            name=re.compile(r"edinburgh\s+journal", re.I),
            masthead_words=re.compile(r"conducted by|author of|editors of|\bedition\b|halfpence"
                                      r"|printed by", re.I),
            # "NUMBER 414.", "No. 1."
            issue_number=re.compile(r"(?:\bNUMBER|\bNo\.?)\s*(\d{1,4})\b", re.I),
            imprint=re.compile(_IMPRINT + r"|^\W*EDINBURGH\s*:|BRADBURY (?:AND|&) EVANS", re.I),
            run_in_capitals_only=True,
        ),
    ]
}


@dataclass(frozen=True)
class Volume:
    """A run of pages to extract: one magazine's PDF (a sample of issues, or a
    whole volume). Its key names its files: page images, YOLO and Document AI
    output, extraction output. Rules come from its magazine."""
    key: str
    magazine: str
    # "build": rules were developed on it. "v2_test": held out for v2, scored
    # with the gold list, and a build text for v3 (decision 0). "test": held out.
    split: str
    pdf: str  # from the repo root
    # PDF pages holding the issues ("7-30"); None: every page.
    pages: str | None = None
    # The volume's printed index: a PDF (default: this volume's PDF) and its
    # pages. None: no index.
    index_pdf: str | None = None
    index_pages: str | None = None

    @property
    def model_output_dir(self) -> str:
        """Where its DocLayout-YOLO and Document AI output goes (from the repo
        root): the 1832 build samples with the other model-choice runs, held-out
        volumes with the v2 article-extraction runs."""
        return MODEL_OUTPUT_DIRS[self.split]

    @property
    def images_dir(self):
        """Page images go next to the PDF: <pdf folder>/images/<key>_images/."""
        from pathlib import Path
        return Path(self.pdf).parent / "images" / f"{self.key}_images"


MODEL_OUTPUT_DIRS = {
    "build": "output/output_images_json_establishing_layout_AIs",
    "v2_test": "output/output_images_json_v2_article_extraction",
    "test": "output/output_images_json_v3_article_extraction",
}

VOLUMES = {
    v.key: v for v in [
        # Development sample (1832, first three issues; v1 evaluated on these).
        Volume("penny", "penny", "build",
               "build_texts/penny_first3sample_inu-30000093220105-1779725606.pdf",
               index_pdf="build_texts/volume_index/"
                         "penny_1832_vol_index_inu-30000093220105-442-443-444-1791991769.pdf"),
        Volume("saturday", "saturday", "build",
               "build_texts/saturday_first3sample_osu-32435051594604-1779834449.pdf"),
        Volume("chambers", "chambers", "build",
               "build_texts/chambers_first3sample_hvd-hwrgz7-1779381321.pdf"),
        # v2's held-out test issues (three issues each, from later volumes, with the
        # volume index; PDF p1 is HathiTrust's cover sheet, then front pieces).
        Volume("penny_1836", "penny", "v2_test",
               "evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/penny_test_3issues_v5_1836_inu-30000093219388-1779827694.pdf",
               pages="6-29", index_pages="4"),
        Volume("saturday_1840", "saturday", "v2_test",
               "evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/saturday_test_3issues_v18.19_1841_mdp-39015082315659-1779842682.pdf",
               pages="6-29", index_pages="4-5"),
        Volume("chambers_1839", "chambers", "v2_test",
               "evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/chambers_test_3issues_v8_1839_mdp-39015024480603-1779384859.pdf",
               pages="7-30", index_pages="4-6"),
        # v3's held-out test issues. Saturday's PDF was replaced after the v3 run
        # to hold the right index (Vol. V); pages 5-28 are unchanged.
        Volume("penny_1838", "penny", "test",
               "evaluation/evaluating_v3_article_extraction/test_texts_extraction_v3/penny_v7_1838_v3_test_3issues.pdf",
               pages="6-25", index_pages="4"),
        Volume("saturday_1834", "saturday", "test",
               "evaluation/evaluating_v3_article_extraction/test_texts_extraction_v3/saturday_v4.5_1834_v3_test_3issues.pdf",
               pages="5-28", index_pages="3-4"),
        Volume("chambers_1843", "chambers", "test",
               "evaluation/evaluating_v3_article_extraction/test_texts_extraction_v3/chambers_v12_1843_v3_test_3issues.pdf",
               pages="7-30", index_pages="4-6"),
    ]
}


def magazine_rules(key: str) -> Magazine:
    """The magazine settings for a volume (or magazine) key."""
    return MAGAZINES[VOLUMES[key].magazine if key in VOLUMES else key]


def page_range(spec: str | None) -> list[int] | None:
    """"7-30" -> [7, ..., 30]; "4" -> [4]; None -> None."""
    if not spec:
        return None
    lo, _, hi = spec.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))
