"""Group ordered page regions into articles.

Walking the content boxes of a magazine in reading order, page after page:

  - a YOLO title box starts a new article (consecutive title boxes before any
    text are one title, e.g. a title plus a subtitle line);
  - a text box whose first words are a run-in head ("Animal Sagacity.—In the
    immense forests ...") starts a new, untitled-by-YOLO article whose title is
    that head; these are the short filler items YOLO never boxes a title for;
  - any other text box continues the current article, including across a page
    break (text at the top of a page before its first title continues the last
    article of the previous page);
  - a masthead (issue-start page) closes the current article: articles don't
    run across issues;
  - figures are linked to the article they sit in, and captions to the nearest
    figure on the page (and so to its article). A "caption" longer than
    CAPTION_MAX_WORDS is read as text (YOLO calls some italic headnotes captions),
    and an all-capitals caption not in brackets as a title ("THE MOLE.");
  - a text box of a few words at the foot of the page is a printer's signature
    ("VOL. I.", "B 2"), not article text.
"""

import re
from dataclasses import dataclass, field

from text import join_regions

MONTHS = ("january february march april may june july august september october "
          "november december").split()
DATE = re.compile(r"\b(" + "|".join(MONTHS) + r")\.?\s+(\d{1,2})\s*,?\s*(1[78]\d\d)", re.I)
ISSUE_NO = re.compile(r"(?:\bNo\.?\s*|\[\s*)(\d{1,4})\s*\.?\s*\]?", re.I)
PAGE_NO = re.compile(r"^\[?\s*(\d{1,4})\s*\.?\]?$")
# Run-in head: 2-6 capitalised words (small connecting words allowed), then a
# full stop and/or dash, then the text carries on with a capital.
RUN_IN = re.compile(
    r"^[\"“‘']?((?:[A-Z][\w'’-]*)(?:\s+(?:[A-Z][\w'’-]*|of|the|and|in|on|at|for|to|a|an)){1,5})"
    r"\s*(?:\.\s*[—–-]{1,2}|[—–]{1,2}|\.)\s*(?=[A-Z“\"‘'])"
)
FIGURE_TITLE = re.compile(r"^([A-Z][A-Z'’ ,&-]{2,60})\.?\s*(?:\[|$)")
CAPTION_MAX_WORDS = 25
SIGNATURE_MAX_WORDS = 3
SIGNATURE_BELOW = 0.88  # share of page height
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

    @property
    def text(self) -> str:
        return join_regions([r.text for r in self.regions])

    @property
    def pages(self) -> list[int]:
        return sorted({r.page for r in self.title_regions + self.regions + self.figures})

    @property
    def all_regions(self) -> list:
        return self.title_regions + self.regions + self.figures + self.captions


def run_in_head(text: str) -> str | None:
    m = RUN_IN.match(text)
    if not m:
        return None
    head = m.group(1)
    words = head.split()
    capitalised = sum(w[0].isupper() for w in words)
    if capitalised < 2 or head.isupper() or words[-1].lower() in SMALL_WORDS:
        return None
    return head


def page_metadata(pg) -> dict:
    """Printed page number from the header/footer furniture; issue date/number
    from the masthead (issue-start pages) or the running header."""
    header = [r for r in pg.regions if r.role == "furniture" and r.y2 < 0.08 * pg.height]
    number = next((int(m.group(1)) for r in header
                   if (m := PAGE_NO.match(r.text.strip())) and not 1700 <= int(m.group(1)) < 1900),
                  None)  # not the year in the running header
    source = " ".join(r.text for r in pg.regions if r.role in ("masthead", "furniture"))
    date = DATE.search(source)
    masthead = [r.text.strip() for r in pg.regions if r.role == "masthead"]
    issue = next((m for t in masthead if (m := PAGE_NO.match(t))), None) or \
        ISSUE_NO.search(" ".join(masthead))
    return {
        "printed_page": number,
        "issue_date": f"{date.group(1).title()} {int(date.group(2))}, {date.group(3)}" if date else None,
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
        for r in pg.ordered:
            if r.role == "caption" and len(r.text.split()) > CAPTION_MAX_WORDS:
                r.role, r.note = "text", "long YOLO caption read as text"
            elif r.role == "caption" and r.text.isupper() and not r.text.lstrip().startswith("["):
                r.role, r.note = "title", "all-capitals YOLO caption read as title"
            if r.role == "text" and len(r.text.split()) <= SIGNATURE_MAX_WORDS \
                    and r.y1 > SIGNATURE_BELOW * pg.height:
                r.role, r.note = "furniture", "printer's signature at foot of page"
                continue
            if r.role == "title":
                if current and current.title_regions and not current.regions \
                        and current.title_regions[-1].page == r.page:
                    current.title = f"{current.title} {r.text}".strip()
                else:
                    start(r.text, "yolo_title")
                current.title_regions.append(r)
            elif r.role == "text":
                head = run_in_head(r.text)
                if head:
                    start(head, "run_in")
                elif current is None:
                    start("", "none")
                current.regions.append(r)
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
    for a in articles:
        # Untitled article opening with an illustration whose title is printed
        # inside the figure box (e.g. "POMPEII. [Restored View of Pompeii.]").
        if a.title_source == "none" and a.figures:
            m = FIGURE_TITLE.match(a.figures[0].text)
            if m:
                a.title, a.title_source = m.group(1), "figure_text"
        a.title = a.title.strip().rstrip(".").strip()
    return articles
