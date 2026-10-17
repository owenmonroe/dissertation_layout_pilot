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
        ),
        Magazine(
            key="saturday",
            columns=2,
            # Its masthead splits "Saturday" and "Magazine" around the seal.
            name=re.compile(r"^\W*(?:the\s+)?saturday\W*$|^\W*magazine\W*$", re.I),
            masthead_words=re.compile(r"saturday|society|committee|knowledge", re.I),
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
            masthead_words=re.compile(r"conducted by|author of|\bedition\b|halfpence", re.I),
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
    split: str  # "build" (rules were developed on it) or "test" (held out)
    pdf: str  # from the repo root
    # PDF pages holding the issues ("7-30"); None: every page.
    pages: str | None = None
    # The volume's printed index: a PDF (default: this volume's PDF) and its
    # pages. None: no index.
    index_pdf: str | None = None
    index_pages: str | None = None

    @property
    def images_dir(self):
        """Page images go next to the PDF: <pdf folder>/images/<key>_images/."""
        from pathlib import Path
        return Path(self.pdf).parent / "images" / f"{self.key}_images"


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
        # Held-out test issues (three issues each, from later volumes, with the
        # volume index; PDF p1 is HathiTrust's cover sheet, then front pieces).
        Volume("penny_1836", "penny", "test",
               "test_texts_extraction/penny_test_3issues_v5_1836_inu-30000093219388-1779827694.pdf",
               pages="6-29", index_pages="4"),
        Volume("saturday_1840", "saturday", "test",
               "test_texts_extraction/saturday_test_3issues_v18.19_1841_mdp-39015082315659-1779842682.pdf",
               pages="6-29", index_pages="4-5"),
        Volume("chambers_1839", "chambers", "test",
               "test_texts_extraction/chambers_test_3issues_v8_1839_mdp-39015024480603-1779384859.pdf",
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
