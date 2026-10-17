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
  - front matter (v2): what sits between a title and the first paragraph is
    the article's front_matter, not text: bylines ("FROM THE REV. WILLIAM
    JONES.", "BY SAMUEL TAYLOR COLERIDGE."), bracketed source lines and
    headnotes ("[From a Correspondent.]", "[July 15th.]"), quoted sayings,
    subtitles ("AN ENGLISH TALE, BY MISS MITFORD."), continuation notes
    ("Continued.", "[Concluded from our last.]"), whether YOLO boxed them as
    a second title, as text, or as the opening of the first paragraph;
  - back matter (v2): what closes an article is its back_matter: a sign-off
    cut from the end of the last paragraph ("...—SOUTHEY."), short source
    boxes ("B. MONTAGU'S Selections."), footnotes ("* ..."; also ones YOLO
    set aside as furniture), bracketed editor's notes, "To be continued";
  - "[To be continued.]" ends its article (back matter), also when printed at
    the end of a paragraph box ("...—Agricultural Journal. (To be continued.)");
  - series and continuations across issues are assigned afterwards
    (series.py);
  - a short all-capitals text box is a title YOLO boxed as text ("PROCESSION
    OF THE IDOL CARS TO THE TEMPLE OF JAGGANATHA");
  - a text box below a printed item rule (rules.py) starts a new item, the
    fillers with no title or run-in head (v2); a footnote under its rule is
    back matter instead;
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

from magazine_rules_config import magazine_rules
from rules import numeric
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
# Run-in head: 2-8 words opening a paragraph, ended by a full stop, "?" or
# "!" and/or a dash, with the text carrying on in capitals: "Animal
# Sagacity.—In the ...", "THE WASP. The manners ...", "CHEAP STEW—Sour ...",
# "WHICH WAS THE GREATER FOOL? In a sermon". Each stop / dash in the opening is
# tried in turn, so "ANECDOTE OF MR. JEFFREY.—" gets past "MR.".
RUN_IN_SEPARATOR = re.compile(r"\s*(?:[.?!]\s*[—–-]{1,2}|[—–]{1,2}|-(?=[A-Z])|[.?!])\s*(?=[A-Z“\"‘'])")
# With a dash after it, a head may have lowercase words, as long as it begins
# and ends capitalised and at least half its words (other than small ones) are
# capitalised: "Science preceding Art.—", "The Secret of great Workers.—". The
# dash is the printer's sign of a head; without one, heads stay strict.
DASHED_HEAD_SHARE = 0.5
INTRODUCES = re.compile(r":\s*[—–-]{0,2}\s*$")
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
INITIALS_DATED = re.compile(r"^\W*(?:[A-Z]\.\s*){1,3}[A-Z][a-z]+\.?,?\s*\d{4}\.?\s*$")  # "D. C. July, 1832."
SUBTITLE = re.compile(r"^\s*[A-Z][A-Z'’ ,&-]{3,40}\.?\s*$")  # "EDINBURGHSHIRE."
CAPTION_MAX_WORDS = 25
OUTRO_MAX_WORDS = 12
CAPS_TITLE_MAX_WORDS = 15
SIGNATURE_MAX_WORDS = 3
SIGNATURE_BELOW = 0.88  # share of page height
# Attribution: a dash then a name or source in capitals / Title Case.
ATTRIBUTION = re.compile(r"[.!?\"”’,;:)]\s*[—–-]{1,2}\s*([A-Z][A-Za-zÀ-ÿæœ'’.,& ]{1,60}?)\.?\s*$")
ATTRIBUTION_MAX_WORDS = 6
# OCR sometimes drops the dash: "... all was calm. Elliot's Letters from the
# North of Europe." v2: a short Title Case final phrase of an article's last
# paragraph is recorded as back matter, with no "looks like a citation" test
# (that lost "Paradise Lost", "History of the Bible"); it doesn't end the
# article, since without a dash it may be an ordinary closing line.
ATTRIBUTION_NO_DASH = re.compile(r"[.!?\"”’]\s+([A-Z][A-Za-zÀ-ÿæœ'’.,& ]{3,80}?)\.?\s*$")
NO_DASH_WORDS = (2, 8)
# A new item needs space (or a column / page break) before it, where the
# magazines print a short rule; paragraphs within an item sit closer.
ITEM_GAP_PX = 20
CAPITALS_OPENING = re.compile(r"^[\"“‘']?(?:[AI]\s+)?[A-Z]{2,}[A-Z'’]*\s+(?![A-Z]{2,}\b)[A-Za-z][a-z]")
BYLINE = re.compile(r"^\W*(?:FROM|BY)\b|^\s*\[\s*(?:Abridged|From|Extracted|Translated|Selected)\b")
BYLINE_MAX_WORDS = 10
END_NOTE = re.compile(r"^\W*to be (?:continued|concluded)\b", re.I)
IMPRINT_BELOW = 0.6  # share of page height
# A publisher's announcement at the end of an issue is imprint (advertising),
# not an article: selling wording in the first line or so of a box, low on
# an issue's last page.
ANNOUNCEMENT = re.compile(r"ready for delivery|\bprice\s+\w*(?:pence|shilling)|\bsewed\b"
                          r"|monthly parts|sold by|\bpublished (?:this|on)\b", re.I)
ANNOUNCEMENT_CHARS = 150
# Editorial notices: a title that is just "NOTICE", "ERRATUM", "TO
# CORRESPONDENTS" (or "NOTICE TO ..."). Not "Notice of ...", the period's
# wording for a biography, and not addresses to readers, which are articles.
EDITORIAL = re.compile(r"^\W*(?:NOTICES?|ERRAT\w*|TO CORRESPONDENTS)\W*$|^\W*NOTICES? TO\b", re.I)
BRACKET_NOTE = re.compile(r"^\W{0,3}\[")
SMALL_WORDS = {"of", "the", "and", "in", "on", "at", "for", "to", "a", "an"}
# Lowercase words allowed in a source title (Owen, v2): prepositions and
# conjunctions as titles print them ("Letters from the North of Europe").
TITLE_SMALL_WORDS = SMALL_WORDS | {"from", "by", "with", "upon", "into", "through", "among",
                                   "over", "under", "against", "after", "before", "near",
                                   "or", "nor", "but", "as"}
# Front matter (v2).
FRONT_TITLE = re.compile(r"^\W*\[|^[\"“‘']|\bBY\b|^\W*(?:continued|concluded)\b", re.I)
CONTINUATION_NOTE = re.compile(r"^\W*(?:continued|concluded)(?: from [^.\]]{0,40})?\.?\W*$", re.I)
# A bracketed source or a continuation note opening the first paragraph:
# "[From The Alhambra, by WASHINGTON IRVING.] MANY are ...",
# "Concluded from No. I. When the ceremony ..."
FRONT_PREFIX = re.compile(r"^\s*(\[[^\]]{3,200}\]|(?:Concluded|Continued) from (?:No\.\s*[IVXLC\d]+|[^.]{1,40})\.)\s*")
BRACKETED = re.compile(r"^\W{0,3}\[.*\]\W*$", re.S)
FIGURE_HEADING = re.compile(r"^\s*[A-Z][A-Z'’ ,&-]{3,}\.\s*$")  # "BRITISH ANIMALS."
# "To be continued" closing a paragraph box, with any source before it:
# "...flour barrels." Agricultural Journal. -To be continued."
CONTINUED_TAIL = re.compile(r"[\s.\-—–(]*\(?\s*To be (?:continued|concluded)\b.{0,30}$", re.I | re.S)
TAIL_SOURCE_MAX_WORDS = 12  # "Murray's Literary History of Galloway. Second Edition."
TITLE_CONTINUATION = re.compile(r"[.,]?\s+((?:Continued|Concluded)\.?)\s*$")  # "ARCHERY. Concluded."
# A table: a box YOLO typed as one, or a text box mostly of figures. Tables
# stay with their article but out of its text (topic modelling, WER): their
# OCR jumbles the columns.
TABLE_MIN_WORDS = 8
# ... and hardly any running prose (three lowercase words in a row), so a
# paragraph about numbers ("the multiples of 9, (9, 18, 27, ...)") stays text.
PROSE_RUN = re.compile(r"\b[a-z]{3,}[,;]?\s+[a-z]{3,}\s+[a-z]{3,}\b")
TABLE_MAX_PROSE = 0.05  # prose runs per word


def is_table(r) -> bool:
    words = r.text.split()
    if r.yolo_type == "table":
        return True
    return len(words) >= TABLE_MIN_WORDS and numeric(r) \
        and len(PROSE_RUN.findall(r.text)) / len(words) <= TABLE_MAX_PROSE
# A bracketed caption printed inside an illustration's box: "[Restored View of Pompeii.]"
BRACKET_CAPTION = re.compile(r"\[[^\]]{3,200}\]?")
FOOTNOTE = re.compile(r"^\s*[*†‡]")
# A short box after an article's text that reads as a source line:
# "B. MONTAGU'S Selections.", "Literary Gazette", "D. C. July, 1832."
SOURCE_BOX_MAX_WORDS = 8


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
    front_regions: list = field(default_factory=list)  # whole boxes of front matter
    back_regions: list = field(default_factory=list)  # whole boxes of back matter
    front_parts: list = field(default_factory=list)  # front matter text, in order
    back_parts: list = field(default_factory=list)  # back matter text, in order
    subsections: list = field(default_factory=list)  # run-in subsection heads
    series: str = ""  # recurring feature ("Biographic Sketches", "The Week"); see series.py
    series_part: str = ""  # numbered part ("I")
    series_evidence: str = ""
    continues_article_id: str = ""  # the earlier part of the same piece
    continued_by_article_id: str = ""
    continuation_evidence: str = ""
    article_type: str = "article"  # or editorial_notice
    tables: list = field(default_factory=list)  # table boxes: kept, but out of the text
    index_entries: list = field(default_factory=list)  # volume index headings (volume_index.py)

    @property
    def text(self) -> str:
        return join_regions([r.body for r in self.regions])

    @property
    def table_text(self) -> str:
        return " | ".join(r.text for r in self.tables)

    @property
    def front_matter(self) -> str:
        return " | ".join(p for p in self.front_parts if p)

    @property
    def back_matter(self) -> str:
        return " | ".join(p for p in self.back_parts if p)

    def add_front(self, r, text=None):
        """Front matter: a whole box (r), or text cut from a box (text)."""
        if text is None:
            self.front_regions.append(r)
            r.role = "front_matter"
            text = r.text
        self.front_parts.append(text.strip())

    def add_back(self, r, text=None):
        if text is None:
            self.back_regions.append(r)
            r.role = "back_matter"
            text = r.text
        self.back_parts.append(text.strip().lstrip("—–- "))

    @property
    def pages(self) -> list[int]:
        return sorted({r.page for r in self.title_regions + self.regions + self.figures
                       + self.tables})

    @property
    def all_regions(self) -> list:
        return (self.title_regions + self.front_regions + self.regions + self.tables
                + self.figures + self.captions + self.back_regions)


def run_in_head(text: str) -> str | None:
    opening = text.lstrip("\"“‘' ")[:RUN_IN_SPAN]
    for sep in RUN_IN_SEPARATOR.finditer(opening):
        head = opening[:sep.start()].strip()
        words = head.split()
        dashed = bool(re.search(r"[—–-]", sep.group()))
        if len(words) < 2 and sep.group().strip() == "-" and not sep.group()[:1].isspace():
            continue  # a hyphen inside the head: "NIGHT-FALL IN ITALY." (not "VATICAN -Perhaps")
        if sep.group().strip()[:1] in "?!":
            if not head.isupper():
                return None  # in mixed case, "?" and "!" end speech: "Then-oh William!"
            head += sep.group().strip()[0]  # "WHICH WAS THE GREATER FOOL?"
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
        content = [w for w in words if w.lower() not in SMALL_WORDS]
        if dashed and words[0][0].isupper() and words[-1][0].isupper() and content \
                and not any(w.endswith(",") for w in words[:-1]) \
                and sum(w[0].isupper() for w in content) / len(content) >= DASHED_HEAD_SHARE:
            return head  # "Science preceding Art.—"
        return None  # the first sentence isn't a heading: no run-in head
    m = CAPITALS_HEAD.match(opening)
    return m.group(1) if m else None


def title_case(words: list[str]) -> bool:
    """Words of a source title: capitalised, or small words in lowercase, and
    not ending on a small word or a comma ("Astronomy, as" isn't a title)."""
    return bool(words) and all(w[0].isupper() or w.lower() in TITLE_SMALL_WORDS
                               or not w[0].isalpha() for w in words) \
        and words[-1].lower() not in TITLE_SMALL_WORDS and not words[-1].endswith(",")


def attribution(text: str):
    """A dash sign-off closing the text ("...nature.—SOUTHEY."): returns the
    sign-off as printed (from its first word to the end), or None. It ends
    the article."""
    m = ATTRIBUTION.search(text)
    if m and len(m.group(1).split()) <= ATTRIBUTION_MAX_WORDS and title_case(m.group(1).split()):
        return text[m.start(1):].strip()
    return None  # e.g. a poem line: "—This Cot his morning ray."


def no_dash_source(text: str):
    """A short Title Case final phrase with no dash ("...all was calm.
    Elliot's Letters from the North of Europe."): recorded as back matter
    when it closes an article's last paragraph; doesn't end the article."""
    m = ATTRIBUTION_NO_DASH.search(text)
    if not m:
        return None
    before = text[:m.start()].split()
    if before and before[-1][:1].isupper():
        return None  # an OCR full stop inside a name: "...the Roya. Academy of Arts."
    words = m.group(1).split()
    if NO_DASH_WORDS[0] <= len(words) <= NO_DASH_WORDS[1] and title_case(words):
        return text[m.start(1):].strip()
    return None


def reads_as_source(text: str) -> bool:
    """A short box that reads as a source line rather than a sentence."""
    if INITIALS_DATED.match(text):
        return True
    words = text.split()
    return 0 < len(words) <= SOURCE_BOX_MAX_WORDS and title_case(
        [w for w in words if re.search(r"[A-Za-z]", w)])


def reads_as_heading(text: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z][\w'’]*", text) if w.lower() not in SMALL_WORDS]
    if not words:
        return False
    return sum(w[0].isupper() for w in words) / len(words) >= HEADING_SHARE


def ruled(current: Article, r) -> bool:
    """A printed item rule between the article's last box and box r."""
    return bool(current.regions) and (r.rule_above or current.regions[-1].rule_below)


def item_break(current: Article, r) -> bool:
    """A printed rule, a rule-sized gap, or a column / page break, before box r."""
    if not current.regions or ruled(current, r):
        return True
    prev = current.regions[-1]
    same_column = prev.page == r.page and prev.column == r.column
    return not same_column or r.y1 - prev.y2 >= ITEM_GAP_PX


def new_item(current: Article, r) -> bool:
    """A text box opening in capitals after a finished sentence, with space (a
    printed rule) or a column/page break before it, starts a new item."""
    if not CAPITALS_OPENING.match(r.text):
        return False
    if not current.regions:
        return bool(current.tables)  # after an item that is only a table
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

    last = None  # the last article closed by a sign-off / end note
    for n_page, pg in enumerate(pages):
        issue_end = n_page + 1 == len(pages) or pages[n_page + 1].issue_start
        if pg.issue_start or issue_seq == 0:
            issue_seq += 1
            current, last = None, None
        in_imprint = False
        magazine = magazine_rules(pg.magazine)
        if issue_end:
            # The imprint often lands in boxes YOLO set aside (abandon) or
            # called a figure (penny's "LONDON:—CHARLES KNIGHT ..."): low on an
            # issue's last page, imprint wording makes them imprint.
            for r in pg.regions:
                if r.role in ("furniture", "figure") and r.y1 > IMPRINT_BELOW * pg.height \
                        and r.text and magazine.imprint.search(r.text):
                    r.role, r.note = "imprint", f"publisher's imprint (YOLO: {r.yolo_type})"
        ordered = pg.ordered
        for i, r in enumerate(ordered):
            words = r.text.split()
            if r.role == "caption" and len(words) > CAPTION_MAX_WORDS:
                r.role, r.note = "text", "long YOLO caption read as text"
            elif r.role == "caption" and r.text.isupper() and not r.text.lstrip().startswith("["):
                r.role, r.note = "title", "all-capitals YOLO caption read as title"
            elif r.role == "caption" and (INTRODUCES.search(r.text)
                                          or not any(f.role == "figure" for f in pg.regions)):
                # A "caption" introducing what follows ("The following are the
                # weights ...:—"), or with no illustration on the page, is text.
                r.role, r.note = "text", "YOLO caption with no illustration to caption, read as text"
            if r.role in ("title", "text") and not re.search(r"[A-Za-z]", r.text):
                r.role, r.note = "furniture", "no words"
                continue
            if r.role == "text" and len(words) <= SIGNATURE_MAX_WORDS \
                    and r.y1 > SIGNATURE_BELOW * pg.height:
                r.role, r.note = "furniture", "printer's signature at foot of page"
                continue
            low = r.y1 > IMPRINT_BELOW * pg.height
            if in_imprint and r.role == "title" and not magazine.imprint.search(r.text):
                in_imprint = False  # a heading after the imprint lines: an article again
            following = ordered[i + 1].text[:ANNOUNCEMENT_CHARS] if i + 1 < len(ordered) else ""
            announcement = low and issue_end and (ANNOUNCEMENT.search(r.text[:ANNOUNCEMENT_CHARS])
                                    or (r.role == "title" and ANNOUNCEMENT.search(following)))
            if r.role in ("title", "text") and (
                    in_imprint or announcement or (low and magazine.imprint.search(r.text))):
                r.role, r.note = "imprint", ("publisher's announcement at end of issue" if announcement
                                             else "publisher's imprint at end of issue")
                in_imprint = True  # what follows is imprint too (agents' lists), until a title
                continue
            if r.role in ("title", "text") and END_NOTE.match(r.text) and len(words) <= 6:
                if current:
                    current.add_back(r)  # "[To be continued.]"
                else:
                    r.role = "back_matter"
                current, last = None, current
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
                current.add_back(r)  # "D. C." signing off the item above
                current, last = None, current
                continue
            if r.role == "title":
                if title_only and FRONT_TITLE.search(r.text):
                    # A second title box that's a source, quoted saying, byline or
                    # continuation note: "[From a Correspondent.]", "AN ENGLISH TALE,
                    # BY MISS MITFORD.", "Continued."
                    current.add_front(r)
                elif title_only:
                    current.title = f"{current.title} {r.text}".strip()
                    current.title_regions.append(r)
                else:
                    start(r.text, "yolo_title")
                    current.title_regions.append(r)
            elif r.role == "text" and is_table(r):
                r.role = "table"
                if current is None:
                    start("", "none")
                current.tables.append(r)
            elif r.role == "text":
                if title_only and (
                        (BYLINE.match(r.text) and len(words) <= BYLINE_MAX_WORDS)
                        or BRACKETED.match(r.text) or CONTINUATION_NOTE.match(r.text)
                        or (SUBTITLE.match(r.text) and len(words) <= 4)):
                    # byline, "[July 15th.]", "[Concluded from our last.]",
                    # a capitals subtitle ("EDINBURGHSHIRE.")
                    current.add_front(r)
                    continue
                if FOOTNOTE.match(r.text) and (current or last):
                    (current or last).add_back(r)  # "* Kilbagie was the greatest ..."
                    continue
                if current and ruled(current, r) and "*" in " ".join(words[:3]):
                    # Under a footnote rule, the asterisk scrambled by OCR ("and *
                    # P.S have since observed"): back matter of the article on the
                    # page whose text has the asterisk.
                    marked = [a for a in articles if a is not current and any(
                        x.page == r.page and "*" in x.text for x in a.regions)]
                    (marked[-1] if marked else current).add_back(r)
                    r.note = "footnote under a printed rule: back matter"
                    current.regions[-1].rule_below = False  # the text after it runs on
                    continue
                if BRACKETED.match(r.text) and ((current and current.regions) or (not current and last)):
                    (current or last).add_back(r)  # "[Such is the history of ...]"
                    r.note = "bracketed editor's note: back matter of the article above"
                    continue
                # No run-in head in a table; and after a paragraph ending in a
                # colon, which introduces what follows ("...as under :-" / a
                # table whose first row reads "Under Seven."; "...of our own
                # day:—" / a quoted poem), a head is at most a subsection.
                introduced = bool(current and current.regions
                                  and INTRODUCES.search(current.regions[-1].text))
                head = None if numeric(r) else run_in_head(r.text)
                capitals_only = magazine.run_in_capitals_only
                if head and current and (
                        title_only
                        or (not attribution(r.text) and (
                            (capitals_only and not head.isupper())
                            or (not item_break(current, r)
                                and (current.subsections
                                     or (capitals_only and current.title_source == "yolo_title")))))):
                    # Run-in subsection, not a new item:
                    #  - a titled article opening on a run-in head ("TWO USEFUL
                    #    RECEIPTS" / "FUMIGATING MIXTURE.—");
                    #  - Chambers: a mixed-case head ("The Bow."), or a head inside
                    #    a titled article ("PLAGUE. CHOLERA" / "CLEANLINESS.—");
                    #  - another head in an article already divided this way;
                    #  unless a rule-sized gap or column/page break comes first, or
                    #  the paragraph ends with its own dash sign-off: a piece with
                    #  its own source is an item ("NEGRO DOCTOR. ... —Edinburgh
                    #  Cabinet Library.").
                    current.subsections.append(head)
                    r.note = f"run-in subsection: {head}"
                    head = None
                if head and introduced:
                    head = None
                if head:
                    start(head, "run_in")
                elif current is None or (new_item(current, r) and not introduced):
                    start("", "none")
                elif ruled(current, r) and not reads_as_source(r.text):
                    # (a source line set below the rule stays back matter)
                    start("", "none")  # a filler: no title, a printed rule above
                    r.note = "new item: printed rule above"
                if not current.regions:
                    m = FRONT_PREFIX.match(r.text)
                    if m:  # "[From The Alhambra, ...] MANY are ...", "Concluded from No. I. When ..."
                        r.front_text = r.text[:m.end()].strip()
                        current.add_front(r, m.group(1))
                current.regions.append(r)
                tail = CONTINUED_TAIL.search(r.text)
                if tail and current.text.strip():
                    close_continued(current, r, tail)
                    current, last = None, current
                    continue
                sign_off = attribution(r.text)
                if sign_off:
                    r.back_text = sign_off
                    current.add_back(r, sign_off.rstrip("."))
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
        for f in figures:
            m = BRACKET_CAPTION.search(f.text or "")
            if m and not f.caption:  # "POMPEII. [Restored View of Pompeii.]"
                f.caption = m.group().strip()
        attach_furniture_matter(pg, articles)
    # An illustration printed above an article's title belongs to that article
    # when it heads the page before any of the article above (a full-width cut,
    # Saturday p12) or carries a printed heading of its own ("BRITISH ANIMALS."
    # over the Mole, penny p20). A figure after the article's own title or text
    # stays with it (penny p4, p12, p13, p17).
    def heads_next(f, a: Article, title) -> bool:
        if f.page != title.page or f.order > title.order:
            return False
        if a.title_regions and any(t.page == f.page and t.order > f.order for t in a.title_regions):
            return False  # it already heads its own article's title
        if any(r.page == f.page and r.order < f.order
               for r in a.title_regions + a.regions):
            return bool(FIGURE_HEADING.match(f.text or ""))
        return True

    for a, nxt in zip(articles, articles[1:]):
        if not (a.figures and nxt.title_regions):
            continue
        title = nxt.title_regions[0]
        moving = [f for f in a.figures if heads_next(f, a, title)]
        if moving:
            nxt.figures[:0] = moving
            a.figures = [f for f in a.figures if f not in moving]
            caps = [c for c in a.captions if c.page == title.page]
            nxt.captions[:0] = caps
            a.captions = [c for c in a.captions if c not in caps]
    articles = [a for a in articles if a.all_regions]
    # A short title-led "article" (a few words) straight before another titled
    # article is the previous article's sign-off that YOLO boxed as a title:
    # "WILLIAM CHAMBERS. / EDINBURGH, 1st February, 1832."
    for prev, a, nxt in zip(articles, articles[1:], articles[2:]):
        if a.title_source == "yolo_title" and not a.figures and nxt.title_source == "yolo_title" \
                and len(a.text.split()) <= OUTRO_MAX_WORDS and a.issue_seq == prev.issue_seq:
            for r in a.title_regions + a.regions:
                prev.add_back(r)
            a.title_regions, a.regions = [], []
    articles = [a for a in articles if a.all_regions]
    for a in articles:
        close_back_matter(a)
    for n, a in enumerate(articles, start=1):  # number without gaps
        a.article_id = f"{a.magazine}_{n:04d}"
    from series import (assign_series_leaders, link_continuations, number_series_parts,
                        series_of_recurring_titles)
    assign_series_leaders(articles)
    for a in articles:
        # Untitled article opening with an illustration whose title is printed
        # inside the figure box (e.g. "POMPEII. [Restored View of Pompeii.]").
        if a.title_source == "none" and a.figures:
            m = FIGURE_TITLE.match(a.figures[0].text)
            if m:
                a.title, a.title_source = m.group(1), "figure_text"
        title, bracket, note = a.title.partition("[")
        if bracket and title.strip():  # "VAN DIEMEN'S LAND. [Concluded from our last.]"
            a.title = title
            a.front_parts.insert(0, f"[{note}".strip())
        m = TITLE_CONTINUATION.search(a.title)
        if m and a.title[:m.start()].strip():  # "ARCHERY. Concluded."
            a.title = a.title[:m.start()]
            a.front_parts.insert(0, m.group(1))
        a.title = a.title.strip().rstrip(".,").strip()
    for a in articles:
        own = magazine_rules(a.magazine).editorial
        if EDITORIAL.search(a.title) or (own and own.search(a.title)):
            a.article_type = "editorial_notice"
    number_series_parts(articles)
    link_continuations(articles)
    series_of_recurring_titles(articles)
    return articles


def close_continued(a: Article, r, tail) -> None:
    """A paragraph box ending "To be continued": the note, and any source
    printed before it (with or without a dash), are back matter, and the
    part ends here."""
    rest = r.text[:tail.start()]
    m = ATTRIBUTION.search(rest)
    source = None
    if m and len(m.group(1).split()) <= TAIL_SOURCE_MAX_WORDS and title_case(m.group(1).split()):
        source = rest[m.start(1):]
    else:
        source = no_dash_source(rest)
    start = rest.rfind(source) if source else tail.start()
    r.back_text = r.text[start:].strip()
    if source:
        a.add_back(r, source.strip().rstrip("."))
    a.add_back(r, tail.group().strip(" -—–().") )


def close_back_matter(a: Article) -> None:
    """Back matter that only shows once the article is complete: short source
    boxes after its text ("B. MONTAGU'S Selections.", "D. C. July, 1832."),
    and a no-dash sign-off closing its last paragraph ("...Elliot's Letters
    from the North of Europe.")."""
    while len(a.regions) > 1 and reads_as_source(a.regions[-1].text):
        r = a.regions.pop()
        a.back_regions.insert(0, r)
        r.role = "back_matter"
        a.back_parts.insert(0, r.text.strip())
    if a.regions and not a.regions[-1].back_text:
        r = a.regions[-1]
        source = no_dash_source(r.text)
        if source and source != r.text.strip():
            r.back_text = source
            a.back_parts.insert(0, source.rstrip("."))


def attach_furniture_matter(pg, articles: list[Article]) -> None:
    """Footnotes and "[To be continued.]" that YOLO set aside as furniture
    (abandon) are back matter: a footnote goes to the article on the page whose
    text has the asterisk, else the page's last article; a continuation note
    to the page's last article."""
    on_page = [a for a in articles if any(r.page == pg.page for r in a.regions)]
    if not on_page:
        return
    for r in pg.regions:
        if r.role != "furniture" or not r.text:
            continue
        if FOOTNOTE.match(r.text):
            marked = [a for a in on_page
                      if any(r2.page == pg.page and "*" in r2.text for r2 in a.regions)]
            (marked or on_page)[-1].add_back(r)
            r.note = "footnote set aside as furniture by YOLO: back matter"
        elif END_NOTE.match(r.text) and len(r.text.split()) <= 6:
            on_page[-1].add_back(r)
            r.note = "continuation note set aside as furniture by YOLO: back matter"
