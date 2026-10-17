"""Duplicate scan pages (v2, decision 9).

Scans sometimes repeat pages: penny PDF pp. 22–23 repeat printed pp. 20–21
(in the HathiTrust copy too). A duplicate's words nearly all match a page
scanned shortly before it. On the development pages a duplicate overlaps its
original by 0.97–1.00 (share of shared words), and every other page overlaps
any of its predecessors by 0.19 at most. Text is used rather than the printed
page number, which OCR often misreads.

Duplicates are left out of article extraction; their boxes stay in the
regions table with role `duplicate_page`, and the pages table records
`duplicate_of`. Article numbers after a duplicate shift accordingly.
"""

import re

from layout import Page

LOOK_BACK = 6  # scans before a page that it may repeat
SAME_TEXT = 0.6  # shared words / all words, over this: the same page
CONTENT = ("title", "text", "caption")


def page_words(pg: Page) -> set[str]:
    text = " ".join(r.text for r in pg.regions if r.role in CONTENT)
    return {w.lower() for w in re.findall(r"[A-Za-z]{4,}", text)}


def find_duplicates(pages: list[Page]) -> dict[int, int]:
    """Scan page -> the earlier scan page it repeats."""
    words = {pg.page: page_words(pg) for pg in pages}
    duplicates = {}
    for i, pg in enumerate(pages):
        mine = words[pg.page]
        if not mine:
            continue
        for earlier in pages[max(0, i - LOOK_BACK):i]:
            if earlier.page in duplicates:
                continue
            theirs = words[earlier.page]
            if len(mine & theirs) / len(mine | theirs) >= SAME_TEXT:
                duplicates[pg.page] = earlier.page
                break
    return duplicates


def set_aside(pg: Page, original: int) -> None:
    pg.issue_start = False  # a repeated first page doesn't start another issue
    for r in pg.regions:
        if r.order or r.role in CONTENT + ("figure", "masthead"):
            r.role, r.order = "duplicate_page", None
            r.note = f"duplicate scan of page {original}"
