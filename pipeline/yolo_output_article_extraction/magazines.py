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

    @property
    def column_names(self) -> list[str]:
        return ["left", "right"] if self.columns == 2 else ["left", "middle", "right"]


# Imprint wording shared by the London/Edinburgh publishers.
_IMPRINT = r"^\W*(?:LONDON\s*:|PRINTED BY|PUBLISHED BY)|publisher'?s agents"

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
                _IMPRINT + r"|^\W*(?:JOHN WILLIAM PARKER|THE COMMITTEE OF GENERAL LITERATURE)"
                r"|WEST STRAND", re.I),
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
