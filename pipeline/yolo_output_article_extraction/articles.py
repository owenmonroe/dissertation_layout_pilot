"""Group ordered page regions into articles.

Walking the content boxes of a magazine in reading order, page after page:

  - a YOLO title box starts a new article (consecutive title boxes before any
    text are one title, e.g. a title plus a subtitle line);
  - a text box whose first words are a run-in head ("Animal Sagacity.—In the
    immense forests ...") starts a new, untitled-by-YOLO article whose title is
    that head; these are the short filler items YOLO never boxes a title for
    (Penny);
  - a text box ending in an attribution ("... swift destruction.—MONTAGU'S
    Dedication.", "...—SOUTHEY.") ends its article; the attribution is kept.
    Short untitled items in the Saturday Magazine end this way;
  - a text box opening with a word in capitals ("I HAVE sat upon the shore",
    "HE whose heart") starts a new untitled article if the current one already
    has text: the magazines set an item's first word in small capitals;
  - a short "FROM THE REV. WILLIAM JONES." / "BY ..." box straight after a
    title is the article's byline, not text;
  - "[To be continued.]" ends its article and is kept as an end note;
  - a short all-capitals text box is a title YOLO boxed as text ("PROCESSION
    OF THE IDOL CARS TO THE TEMPLE OF JAGGANATHA");
  - any other text box continues the current article, including across a page
    break (text at the top of a page before its first title continues the last
    article of the previous page);
  - a masthead (issue-start page) closes the current article: articles don't
    run across issues; the publisher's imprint at the end of an issue
    ("LONDON: JOHN WILLIAM PARKER, WEST STRAND") is not an article;
  - figures are linked to the article they sit in, and captions to the nearest
    figure on the page (and so to its article). A "caption" longer than
    CAPTION_MAX_WORDS is read as text (YOLO calls some italic headnotes captions),
    and an all-capitals caption not in brackets as a title ("THE MOLE.");
  - a text box of a few words at the foot of the page is a printer's signature
    ("VOL. I.", "B 2"), not article text.
"""

import re
from dataclasses import dataclass, field

from magazine_rules_config import MAGAZINES
from text import SENTENCE_END, join_regions

MONTHS = ("january february march april may june july august september october "
          "november december").split()
# Year optional: some mastheads lose it to OCR (run_extraction borrows it).
DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})\b(?:\s*,?\s*(1[78]\d\d))?", re.I)
ISSUE_NO = re.compile(r"(?:\bN[oº°]\.?\s*|\[\s*)(\d{1,4})\s*\.?\s*\]?", re.I)
PAGE_NO = re.compile(r"^\[?\s*(\d{1,4})\s*\.?\]?$")
# An issue number on its own in the masthead: "1.]", "No. 2.", "Nº 3.", and
# "2.1" / "2.l" (the closing bracket of "2.]" misread). Punctuation is ignored.
ISSUE_LABEL = re.compile(r"^\W*(?:N[oº°]\.?\s*)?(\d{1,4})\s*(?:\.\s*[\]1lI|]?|\])?\W*$")


def issue_number(texts: list[str]) -> int | None:
    for t in texts:
        m = ISSUE_LABEL.match(t.strip())
        if m and not 1700 <= int(m.group(1)) < 1900:  # not the year
            return int(m.group(1))
    m = ISSUE_NO.search(" ".join(texts))
    return int(m.group(1)) if m else None
# Run-in head: 2-8 words opening a paragraph, ended by a full stop and/or
# dash, with the text carrying on in capitals: "Animal Sagacity.—In the ...",
# "THE WASP. The manners ...", "CHEAP STEW—Sour ...". Each full stop / dash in
# the opening is tried in turn, so "ANECDOTE OF MR. JEFFREY.—" gets past "MR.".
RUN_IN_SEPARATOR = re.compile(r"\s*(?:\.\s*[—–-]{1,2}|[—–]{1,2}|-(?=[A-Z])|\.)\s*(?=[A-Z“\"‘'])")
RUN_IN_SPAN = 90  # characters of the paragraph the head can take up
# OCR sometimes loses the stop/dash after a head ("NIGHT-FALL IN ITALY In Mr.
# Bell's ..."): 3+ words in capitals opening the paragraph, then a normal word.
CAPITALS_HEAD = re.compile(r"^((?:[A-Z][A-Z'’-]+|OF|THE|AND|IN|ON|AT|FOR|TO|A|AN)"
                           r"(?:\s+(?:[A-Z][A-Z'’-]+|OF|THE|AND|IN|ON|AT|FOR|TO|A|AN)){2,7})"
                           r"\s+(?=[A-Z][a-z])")
ABBREVIATIONS = {"st", "mr", "mrs", "dr", "messrs", "capt", "col", "gen", "rev", "sir",
                 "lord", "esq", "no", "vol", "mt"}
# A title printed inside a figure box: its opening run of capitals.
# A YOLO "title" is a real heading only if it reads like one: capitals or
# Title Case. Lowercase lines and epigraphs ("system of human society",
# "With merit needless, and without it vain") are text YOLO mislabelled.
HEADING_SHARE = 0.6
FIGURE_TITLE = re.compile(r"^([A-Z][A-Z'’ ,&-]{2,80}?)\s*(?:[.(\[]|$)")
# A title box holding only initials ("D. C.") signs off the item above it.
INITIALS = re.compile(r"^\W*(?:[A-Z]\.\s*){1,3}\W*$")
CAPTION_MAX_WORDS = 25
OUTRO_MAX_WORDS = 12
CAPS_TITLE_MAX_WORDS = 15
SIGNATURE_MAX_WORDS = 3
SIGNATURE_BELOW = 0.88  # share of page height
# Attribution: a dash then a name or source in capitals / Title Case.
ATTRIBUTION = re.compile(r"[.!?\"”’,;:)]\s*[—–-]{1,2}\s*([A-Z][A-Za-z'’.,& ]{1,60}?)\.?\s*$")
ATTRIBUTION_MAX_WORDS = 6
# OCR sometimes drops the dash: "... all was calm. Elliot's Letters from the
# North of Europe." Without a dash, only a source citation counts: Title Case,
# with a possessive or ending in a word like Journal / Review.
ATTRIBUTION_NO_DASH = re.compile(r"[.!?\"”’]\s+([A-Z][A-Za-z'’.,& ]{3,80}?)\.?\s*$")
SOURCE_WORDS = {"journal", "magazine", "review", "travels", "history", "economy", "cyclopaedia",
                "cyclopedia", "letters", "anecdotes", "companion", "knowledge", "sketches", "tour"}
# A new item needs space (or a column / page break) before it, where the
# magazines print a short rule; paragraphs within an item sit closer.
ITEM_GAP_PX = 20
CAPITALS_OPENING = re.compile(r"^[\"“‘']?(?:[AI]\s+)?[A-Z]{2,}[A-Z'’]*\s+(?![A-Z]{2,}\b)[A-Za-z][a-z]")
BYLINE = re.compile(r"^\W*(?:FROM|BY)\b|^\s*\[\s*(?:Abridged|From|Extracted|Translated|Selected)\b")
BYLINE_MAX_WORDS = 10
END_NOTE = re.compile(r"^\W*to be (?:continued|concluded)\b", re.I)
IMPRINT_BELOW = 0.6  # share of page height
BRACKET_NOTE = re.compile(r"^\W{0,3}\[")
SMALL_WORDS = {"of", "the", "and", "in", "on", "at", "for", "to", "a", "an"}


@dataclass
class Article:
    article_id: str
    magazine: str
    issue_seq: int
    title: str
    title_source: str  # yolo_title / run_in / figure_text / none
    regions: list = field(default_factory=list)
    title_regions: list = field(default_factory=list)
    figures: list = field(default_factory=list)
    captions: list = field(default_factory=list)
    notes: list = field(default_factory=list)  # byline / end-note boxes
    subsections: list = field(default_factory=list)  # run-in subsection heads
    byline: str = ""
    attribution: str = ""
    end_note: str = ""
    title_note: str = ""  # bracketed part of a title: "[Concluded from our last.]"

    @property
    def text(self) -> str:
        return join_regions([r.text for r in self.regions])

    @property
    def pages(self) -> list[int]:
        return sorted({r.page for r in self.title_regions + self.regions + self.figures})

    @property
    def all_regions(self) -> list:
        return self.title_regions + self.regions + self.figures + self.captions + self.notes


def run_in_head(text: str) -> str | None:
    opening = text.lstrip("\"“‘' ")[:RUN_IN_SPAN]
    for sep in RUN_IN_SEPARATOR.finditer(opening):
        head = opening[:sep.start()].strip()
        words = head.split()
        if len(words) < 2 and sep.group().strip() == "-":
            continue  # a hyphen inside the head: "NIGHT-FALL IN ITALY."
        if len(words) == 1 and words[0].isupper() and len(words[0]) >= 4:
            return head  # one word in capitals: "HAARLEM. We paid ...", "FOWLS."
        if not 2 <= len(words) <= 8:
            return None  # one word, or a whole sentence: not a heading
        if words[-1].lower().strip(".") in ABBREVIATIONS:
            continue  # "Returning to the St. Lawrence", "MR. JEFFREY"
        if re.fullmatch(r"[A-Z]{1,2}", words[-1]) or "." in words[-1]:
            continue  # initials: "Alexander Adam, LL.D.", "Monroe County, N.Y."
        heading_words = all(w[0].isupper() or w.lower() in SMALL_WORDS for w in words)
        capitalised = sum(w[0].isupper() for w in words)
        if heading_words and capitalised >= 2 and words[0][0].isupper() \
                and words[-1].lower() not in SMALL_WORDS:
            return head
        return None  # the first sentence isn't a heading: no run-in head
    m = CAPITALS_HEAD.match(opening)
    return m.group(1) if m else None


def attribution(text: str) -> str | None:
    m = ATTRIBUTION.search(text)
    if m:
        words = m.group(1).split()
        title_case = all(w[0].isupper() or w.lower() in SMALL_WORDS for w in words)
        if len(words) <= ATTRIBUTION_MAX_WORDS and title_case:
            return m.group(1).strip()
        return None  # e.g. a poem line: "—This Cot his morning ray."
    m = ATTRIBUTION_NO_DASH.search(text)
    if m:
        words = m.group(1).split()
        title_case = all(w[0].isupper() or w.lower() in SMALL_WORDS for w in words)
        cites = any("'s" in w or "’s" in w for w in words) or words[-1].lower().strip(".") in SOURCE_WORDS
        if 2 <= len(words) <= 8 and title_case and cites:
            return m.group(1).strip()
    return None


def reads_as_heading(text: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z][\w'’]*", text) if w.lower() not in SMALL_WORDS]
    if not words:
        return False
    return sum(w[0].isupper() for w in words) / len(words) >= HEADING_SHARE


def item_break(current: Article, r) -> bool:
    """A rule-sized gap, or a column / page break, before box r."""
    if not current.regions:
        return True
    prev = current.regions[-1]
    same_column = prev.page == r.page and prev.column == r.column
    return not same_column or r.y1 - prev.y2 >= ITEM_GAP_PX


def new_item(current: Article, r) -> bool:
    """A text box opening in capitals after a finished sentence, with space (a
    printed rule) or a column/page break before it, starts a new item."""
    if not current.regions or not CAPITALS_OPENING.match(r.text):
        return False
    prev = current.regions[-1]
    if not SENTENCE_END.search(prev.text):
        return False
    same_column = prev.page == r.page and prev.column == r.column
    return not same_column or r.y1 - prev.y2 >= ITEM_GAP_PX


def page_metadata(pg, extra_text: str = "") -> dict:
    """Printed page number from the header/footer furniture; issue date/number
    from the masthead (issue-start pages) or the running header. extra_text:
    unboxed OCR text, which on issue-start pages holds masthead lines YOLO
    drew no box for."""
    header = [r for r in pg.regions if r.role == "furniture" and r.y2 < 0.08 * pg.height]
    number = next((int(m.group(1)) for r in header
                   if (m := PAGE_NO.match(r.text.strip())) and not 1700 <= int(m.group(1)) < 1900),
                  None)  # not the year in the running header
    source = " ".join(r.text for r in pg.regions if r.role in ("masthead", "furniture"))
    source += " " + extra_text if pg.issue_start else ""
    date = DATE.search(source)
    masthead = [r.text.strip() for r in pg.regions if r.role == "masthead"]
    if pg.issue_start:
        masthead += extra_text.split(" | ")
    date_text = None
    if date:
        date_text = f"{date.group(1).title()} {int(date.group(2))}"
        date_text += f", {date.group(3)}" if date.group(3) else ""
    return {
        "printed_page": number,
        "issue_date": date_text,
        "issue_no": issue_number(masthead) if pg.issue_start else None,
    }


def segment(pages: list) -> list[Article]:
    articles: list[Article] = []
    current = None
    issue_seq = 0

    def start(title, source):
        nonlocal current
        current = Article(f"{pages[0].magazine}_{len(articles) + 1:04d}", pages[0].magazine,
                          issue_seq, title, source)
        articles.append(current)
        return current

    last = None  # the last article closed by an attribution / end note
    for pg in pages:
        if pg.issue_start or issue_seq == 0:
            issue_seq += 1
            current, last = None, None
        in_imprint = False
        magazine = MAGAZINES[pg.magazine]
        for r in pg.ordered:
            words = r.text.split()
            if r.role == "caption" and len(words) > CAPTION_MAX_WORDS:
                r.role, r.note = "text", "long YOLO caption read as text"
            elif r.role == "caption" and r.text.isupper() and not r.text.lstrip().startswith("["):
                r.role, r.note = "title", "all-capitals YOLO caption read as title"
            if r.role in ("title", "text") and not re.search(r"[A-Za-z]", r.text):
                r.role, r.note = "furniture", "no words"
                continue
            if r.role == "text" and len(words) <= SIGNATURE_MAX_WORDS \
                    and r.y1 > SIGNATURE_BELOW * pg.height:
                r.role, r.note = "furniture", "printer's signature at foot of page"
                continue
            if r.role in ("title", "text") and (in_imprint or (
                    r.y1 > IMPRINT_BELOW * pg.height and magazine.imprint.search(r.text))):
                r.role, r.note = "imprint", "publisher's imprint at end of issue"
                in_imprint = True  # the rest of the page is imprint too (agents' lists)
                continue
            if r.role in ("title", "text") and END_NOTE.match(r.text) and len(words) <= 6:
                if current:
                    current.end_note = r.text
                    current.notes.append(r)
                r.role, current, last = "end_note", None, current
                continue
            if r.role == "title" and not reads_as_heading(r.text):
                r.role, r.note = "text", "YOLO title that doesn't read as a heading, read as text"
            if r.role == "title" and magazine.name.search(r.text) and not pg.issue_start:
                r.role, r.note = "furniture", "magazine name"
                continue
            title_only = current and current.title_regions and not current.regions \
                and current.title_regions[-1].page == r.page
            if r.role == "text" and r.text.isupper() and 2 <= len(words) <= CAPS_TITLE_MAX_WORDS \
                    and not (title_only and BYLINE.match(r.text)):
                r.role, r.note = "title", "all-capitals YOLO text read as title"
            if r.role == "title" and INITIALS.match(r.text) and current and current.regions:
                current.attribution = r.text.strip()
                current.notes.append(r)
                r.role, current = "attribution", None
                continue
            if r.role == "title":
                if title_only:
                    current.title = f"{current.title} {r.text}".strip()
                else:
                    start(r.text, "yolo_title")
                current.title_regions.append(r)
            elif r.role == "text":
                if title_only and BYLINE.match(r.text) and len(words) <= BYLINE_MAX_WORDS:
                    current.byline = r.text
                    current.notes.append(r)
                    r.role = "byline"
                    continue
                head = run_in_head(r.text)
                capitals_only = magazine.run_in_capitals_only
                if head and current and (
                        title_only
                        or (capitals_only and not head.isupper())
                        or (not item_break(current, r)
                            and (current.subsections
                                 or (capitals_only and current.title_source == "yolo_title")))):
                    # Run-in subsection, not a new item:
                    #  - a titled article opening on a run-in head ("TWO USEFUL
                    #    RECEIPTS" / "FUMIGATING MIXTURE.—");
                    #  - Chambers: a mixed-case head ("The Bow."), or a head inside
                    #    a titled article ("PLAGUE. CHOLERA" / "CLEANLINESS.—");
                    #  - another head in an article already divided this way;
                    #  unless a rule-sized gap or column/page break comes first.
                    current.subsections.append(head)
                    r.note = f"run-in subsection: {head}"
                    head = None
                if current is None and last and BRACKET_NOTE.match(r.text):
                    current = last  # "[Such is the history of ...]": editor's note on it
                    r.note = "bracketed editor's note joined to the article above"
                elif head:
                    start(head, "run_in")
                elif current is None or new_item(current, r):
                    start("", "none")
                current.regions.append(r)
                source = attribution(r.text)
                if source:
                    current.attribution = source
                    current, last = None, current
            elif r.role == "figure":
                if current is None:
                    start("", "none")
                current.figures.append(r)
        figures = [f for f in pg.regions if f.role == "figure"]
        for cap in (r for r in pg.ordered if r.role == "caption"):
            if figures:
                fig = min(figures, key=lambda f: abs(f.cy - cap.cy) + abs(f.cx - cap.cx))
                fig.caption = f"{fig.caption} {cap.text}".strip()
                owner = next((a for a in articles if fig in a.figures), None)
                if owner:
                    owner.captions.append(cap)
    # An illustration printed above its article's title opens an "article" of
    # its own with no text; move it into the article whose title follows it.
    for a, nxt in zip(articles, articles[1:]):
        if a.figures and not a.regions and nxt.pages and nxt.pages[0] == a.pages[-1]:
            nxt.figures[:0], nxt.captions[:0] = a.figures, a.captions
            a.figures, a.captions = [], []
    articles = [a for a in articles if a.all_regions]
    # A short title-led "article" (a few words) straight before another titled
    # article is the previous article's sign-off that YOLO boxed as a title:
    # "WILLIAM CHAMBERS. / EDINBURGH, 1st February, 1832."
    for prev, a, nxt in zip(articles, articles[1:], articles[2:]):
        if a.title_source == "yolo_title" and not a.figures and nxt.title_source == "yolo_title" \
                and len(a.text.split()) <= OUTRO_MAX_WORDS and a.issue_seq == prev.issue_seq:
            prev.attribution = " ".join(filter(None, [prev.attribution, a.title, a.text]))
            prev.notes += a.title_regions + a.regions
            a.title_regions, a.regions = [], []
    articles = [a for a in articles if a.all_regions]
    for n, a in enumerate(articles, start=1):  # number without gaps
        a.article_id = f"{a.magazine}_{n:04d}"
    for a in articles:
        # Untitled article opening with an illustration whose title is printed
        # inside the figure box (e.g. "POMPEII. [Restored View of Pompeii.]").
        if a.title_source == "none" and a.figures:
            m = FIGURE_TITLE.match(a.figures[0].text)
            if m:
                a.title, a.title_source = m.group(1), "figure_text"
        title, bracket, note = a.title.partition("[")
        if bracket and title.strip():
            a.title, a.title_note = title, f"[{note}".strip()
        a.title = a.title.strip().rstrip(".").strip()
    return articles
