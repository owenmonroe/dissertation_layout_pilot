"""The volume index as a check on items (v2, decision 4).

Each volume ends with an alphabetical index ("Air-balloon, 8.", "Angelo,
anecdote of Michael, 8.", "British animals, the Dormouse, 12; the Swallow,
ib.; the Mole, 20."). Its entries are parsed from the PDF's text layer
(HathiTrust/Google OCR), then matched by their distinctive words to the
articles on the printed pages they cite. This produces:

  - an index check table, one row per entry citing a page in the run:
      - matched: the entry's words appear in one article on that page;
      - shared: another entry matched the same article. Usually the same
        item indexed twice ("Swallow, account of" / "British animals, the
        Swallow"), but it can mean two items merged into one article;
      - unmatched: no article on the page has the entry's words. The item
        may be missing or merged, or the index OCR may be garbled;
  - an `index_entries` column on each article: the index headings that
    matched it, as subject terms (and a title for untitled fillers).

The index doesn't change the articles; it flags pages to check.

Parsing: the index is printed in three columns with a hanging indent. A line
at a column's left margin starts an entry, and so does a line starting with a
capital after an entry that ended on a page number. Indented lines run on.
The list of illustrations at the end is left out.
"""

import re
import statistics
from dataclasses import dataclass, field
from pathlib import Path

PAGE_NUMBER = re.compile(r"(?<![\w.])(?<!No\. )(\d{1,3})(?!\d)(?=\s*[.,;)]|\s*$)")
ENDS_ON_PAGE = re.compile(r"\d{1,3}\s*\.?\s*$")
ILLUSTRATIONS = re.compile(r"\bLIST\b.*\bILLUSTRATION|\bLIST\s*$", re.I)
GENERIC = {
    "notice", "notices", "account", "description", "remarks", "remark", "instance", "instances",
    "anecdote", "anecdotes", "poem", "lines", "advantages", "observations", "review", "reviewed",
    "letters", "memoir", "character", "history", "nature", "study", "uses", "with", "from",
    "their", "this", "that", "upon", "page", "some", "great", "means", "curious", "remarkable",
    "singular", "example", "particulars", "further", "respecting", "relative", "facts", "tale",
}
STEM = 5  # letters compared, so plurals and small OCR slips still match


@dataclass
class Entry:
    text: str
    index_page: int
    column: int
    pages: list = field(default_factory=list)

    @property
    def heading(self) -> str:
        """The entry up to its first page number: "Angelo, anecdote of Michael"."""
        m = PAGE_NUMBER.search(self.text)
        return self.text[:m.start()].strip(" ,.;") if m else self.text

    @property
    def words(self) -> set[str]:
        return {w for w in stems(self.heading) if w not in {g[:STEM] for g in GENERIC}}


def parse_index(pdf: Path, pages: list[int] | None = None) -> list[Entry]:
    """Entries from the index pages of a PDF: the given pages (1-based), or
    every page headed INDEX."""
    import fitz  # PyMuPDF

    entries: list[Entry] = []
    with fitz.open(pdf) as doc:
        for page_no, page in enumerate(doc):
            if pages and page_no + 1 not in pages:
                continue
            words = page.get_text("words")
            head = [w for w in words if w[4].strip(".,") == "INDEX"]
            if not head and not pages:
                continue  # HathiTrust's cover sheet
            top = head[0][3] if head else 0.06 * page.rect.height  # below the heading
            words = [w for w in words if w[1] > top]
            if not words:
                continue
            x0, x1 = min(w[0] for w in words), max(w[2] for w in words)
            width = (x1 - x0) / 3
            for col in range(3):
                lines = column_lines([w for w in words
                                      if x0 + col * width - 3 <= w[0] < x0 + (col + 1) * width - 3])
                if not lines:
                    continue
                starts = sorted(x for x, _ in lines)
                margin = statistics.median(starts[:max(3, len(starts) // 3)])
                for x, text in lines:
                    if ILLUSTRATIONS.search(text):
                        return finish(entries)
                    prev = entries[-1] if entries else None
                    new = (x <= margin + 4
                           or (prev and ENDS_ON_PAGE.search(prev.text) and text[:1].isupper()))
                    if new or prev is None:
                        entries.append(Entry(text, page_no, col))
                    else:
                        prev.text += " " + text
    return finish(entries)


def column_lines(words) -> list[tuple[float, str]]:
    """(left x, text) of each printed line in one column, top to bottom."""
    lines: list[list] = []
    for w in sorted(words, key=lambda w: w[1]):
        for line in lines:
            if abs(line[0][1] - w[1]) < 3.5:
                line.append(w)
                break
        else:
            lines.append([w])
    out = []
    for line in sorted(lines, key=lambda l: l[0][1]):
        line.sort(key=lambda w: w[0])
        out.append((line[0][0], " ".join(w[4] for w in line)))
    return out


def finish(entries: list[Entry]) -> list[Entry]:
    for e in entries:
        e.text = re.sub(r"\s+([,.;])", r"\1", e.text)
        e.pages = [int(n) for n in PAGE_NUMBER.findall(e.text)]
    return entries


def printed_pages(page_rows: list[dict]) -> dict[int, int]:
    """Scan page -> printed page, filling pages with no printed number (issue
    first pages, unread numbers) from their neighbours."""
    known = {r["page"]: r["printed_page"] for r in page_rows if r.get("printed_page")}
    out, prev = {}, None
    for r in page_rows:
        n = known.get(r["page"])
        out[r["page"]] = n if n else (prev + 1 if prev else None)
        prev = out[r["page"]]
    first = next((p for p, n in out.items() if n), None)
    for p in sorted(out):
        if out[p] is None and first is not None:
            out[p] = out[first] - (first - p)
    return out


def stems(text: str) -> set[str]:
    return {w.lower()[:STEM] for w in re.findall(r"[A-Za-z]{4,}", text)}


def check_index(entries: list[Entry], articles: list, page_rows: list[dict]) -> list[dict]:
    """Match entries to articles on the printed pages they cite; returns the
    index check rows and fills each article's index_entries."""
    printed = printed_pages(page_rows)
    in_run = set(printed.values())
    rows = []
    matched_by: dict[str, list] = {}
    for e in entries:
        for page in sorted(set(p for p in e.pages if p in in_run)):
            scans = [s for s, n in printed.items() if n == page]
            candidates = []
            for a in articles:
                text = " ".join([a.title] + [r.text for r in a.all_regions if r.page in scans])
                if not any(r.page in scans for r in a.all_regions):
                    continue
                found = e.words & stems(text)
                if found:
                    # words in the title count twice: "Swallow, account of" is
                    # the Swallow, though the Dormouse's text mentions swallows
                    candidates.append((len(found) + len(found & stems(a.title)), a, found))
            best = max(candidates, key=lambda c: c[0], default=None)
            row = {"index_entry": e.text, "heading": e.heading, "printed_page": page,
                   "scan_pages": ";".join(map(str, scans)), "article_id": None,
                   "article_title": None, "matched_words": None, "status": "unmatched"}
            if best:
                _, a, found = best
                row.update(article_id=a.article_id, article_title=a.title,
                           matched_words=", ".join(sorted(found)), status="matched")
                matched_by.setdefault(a.article_id, []).append(row)
                if e.heading not in a.index_entries:
                    a.index_entries.append(e.heading)
            rows.append(row)
    for shared in (rs for rs in matched_by.values() if len(rs) > 1):
        for row in shared:
            row["status"] = "shared"
    return rows
