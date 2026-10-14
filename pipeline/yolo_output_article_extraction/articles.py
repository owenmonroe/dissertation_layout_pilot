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

from text import SENTENCE_END, join_regions

MONTHS = ("january february march april may june july august september october "
          "november december").split()
# Year optional: some mastheads lose it to OCR (run_extraction borrows it).
DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})\b(?:\s*,?\s*(1[78]\d\d))?", re.I)
ISSUE_NO = re.compile(r"(?:\bN[oº°]\.?\s*|\[\s*)(\d{1,4})\s*\.?\s*\]?", re.I)
PAGE_NO = re.compile(r"^\[?\s*(\d{1,4})\s*\.?\]?$")
# Run-in head: 2-6 capitalised words (small connecting words allowed), then a
# full stop and/or dash, then the text carries on with a capital.
RUN_IN = re.compile(
    r"^[\"“‘']?((?:[A-Z][\w'’-]*)(?:\s+(?:[A-Z][\w'’-]*|of|the|and|in|on|at|for|to|a|an)){1,5})"
    r"\s*(?:\.\s*[—–-]{1,2}|[—–]{1,2}|\.)\s*(?=[A-Z“\"‘'])"
)
# A title printed inside a figure box: its opening run of capitals.
FIGURE_TITLE = re.compile(r"^([A-Z][A-Z'’ ,&-]{2,80}?)\s*(?:[.(\[]|$)")
# A title box holding only initials ("D. C.") signs off the item above it.
INITIALS = re.compile(r"^\W*(?:[A-Z]\.\s*){1,3}\W*$")
CAPTION_MAX_WORDS = 25
CAPS_TITLE_MAX_WORDS = 15
SIGNATURE_MAX_WORDS = 3
SIGNATURE_BELOW = 0.88  # share of page height
# Attribution: a dash then a name or source in capitals / Title Case.
ATTRIBUTION = re.compile(r"[.!?\"”’,;:)]\s*[—–-]{1,2}\s*([A-Z][A-Za-z'’.,& ]{1,60}?)\.?\s*$")
ATTRIBUTION_MAX_WORDS = 6
# A new item needs space (or a column / page break) before it, where the
# magazines print a short rule; paragraphs within an item sit closer.
ITEM_GAP_PX = 20
CAPITALS_OPENING = re.compile(r"^[\"“‘']?(?:[AI]\s+)?[A-Z]{2,}[A-Z'’]*\s+(?![A-Z]{2,}\b)[A-Za-z][a-z]")
BYLINE = re.compile(r"^\W*(?:FROM|BY)\b|^\s*\[\s*(?:Abridged|From|Extracted|Translated|Selected)\b")
BYLINE_MAX_WORDS = 10
END_NOTE = re.compile(r"^\W*to be (?:continued|concluded)\b", re.I)
IMPRINT = re.compile(
    r"^\W*(?:LONDON\s*:|PRINTED BY|PUBLISHED BY|JOHN WILLIAM PARKER"
    r"|THE COMMITTEE OF GENERAL LITERATURE)|WEST STRAND|PALL[- ]MALL EAST|publisher'?s agents",
    re.I)
IMPRINT_BELOW = 0.6  # share of page height
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
    m = RUN_IN.match(text)
    if not m:
        return None
    head = m.group(1)
    words = head.split()
    capitalised = sum(w[0].isupper() for w in words)
    if capitalised < 2 or words[-1].lower() in SMALL_WORDS:
        return None
    if head.isupper() and not re.search(r"[—–-]", m.group(0)[len(head):]):
        return None  # all-capitals heads ("HUMMING BIRDS.—") need the dash
    return head


def attribution(text: str) -> str | None:
    m = ATTRIBUTION.search(text)
    if not m:
        return None
    words = m.group(1).split()
    title_case = all(w[0].isupper() or w.lower() in SMALL_WORDS for w in words)
    if len(words) > ATTRIBUTION_MAX_WORDS or not title_case:
        return None  # e.g. a poem line: "—This Cot his morning ray."
    return m.group(1).strip()


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
    issue = next((m for t in masthead
                  if (m := PAGE_NO.match(t)) and not 1700 <= int(m.group(1)) < 1900), None) or \
        ISSUE_NO.search(" ".join(masthead))
    date_text = None
    if date:
        date_text = f"{date.group(1).title()} {int(date.group(2))}"
        date_text += f", {date.group(3)}" if date.group(3) else ""
    return {
        "printed_page": number,
        "issue_date": date_text,
        "issue_no": int(issue.group(1)) if issue else None,
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

    for pg in pages:
        if pg.issue_start or issue_seq == 0:
            issue_seq += 1
            current = None
        in_imprint = False
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
                    r.y1 > IMPRINT_BELOW * pg.height and IMPRINT.search(r.text))):
                r.role, r.note = "imprint", "publisher's imprint at end of issue"
                in_imprint = True  # the rest of the page is imprint too (agents' lists)
                continue
            if r.role in ("title", "text") and END_NOTE.match(r.text) and len(words) <= 6:
                if current:
                    current.end_note = r.text
                    current.notes.append(r)
                r.role, current = "end_note", None
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
                if head:
                    start(head, "run_in")
                elif current is None or new_item(current, r):
                    start("", "none")
                current.regions.append(r)
                source = attribution(r.text)
                if source:
                    current.attribution = source
                    current = None
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
