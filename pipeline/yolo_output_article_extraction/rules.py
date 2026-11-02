"""Printed rules between items (v2, decision 4).

The magazines print a short horizontal rule, centred in the column, between
items that have no title of their own (the fillers). YOLO doesn't box these
rules, so they're found in the page image: a row of solid ink, 60 px or more
long (at 300 DPI), with clear space just above and below it. A tilted rule shows
up on a few neighbouring rows; those detections are grouped into one rule.

A rule counts as an item rule only when it is centred in its column of the
page grid (within CENTRED of the column width). This leaves out:
- the short underlines under Chambers titles (the box above is a title);
- rules under captions and inside illustrations;
- table total lines and footnote rules, which sit to one side (and any rule
  inside or under a box of figures).

An item rule in the gap between two text boxes marks the lower box as opening
a new item. A rule inside a text box splits the box at the rule ("...Field
Sports of the North of Europe." / "CHEESE HOPPERS.—...").
"""

import numpy as np
from PIL import Image

from layout import Page, Region, column_of, column_width
from text import FOOTNOTE, join_lines

FOOT_REACH_PX = 80  # a set-aside box this close below a rule sits under it
DARK = 60  # grey levels below the page's median that count as ink
MIN_LEN_PX = 60
MAX_SHARE = 0.6  # longer than this share of the content width: not an item rule
CLEAR_PX = 6  # rows checked above and below the rule
CLEAR_INK = 0.08  # most ink allowed in those rows, over the rule's span
SOLID = 0.85  # least ink along the rule itself
GAP_PX = 3  # breaks in the line bridged
GROUP_PX = 30  # detections this close vertically are one (tilted) rule,
GROUP_GAP_PX = 150  # if no further apart than this sideways (not two columns' rules)
CENTRED = 0.12  # rule centre's offset from the column centre, as a share of column width
TABLE_SHARE = 0.3  # share of words with figures that makes a box a table
EDGE_PX = 20  # a rule this close to a box's edge is in the gap, not inside


def longest_run(row: np.ndarray) -> tuple[int, int]:
    """(length, start) of the longest run of ink in a row, bridging small gaps."""
    best, start, last = (0, 0), None, None
    for x in np.flatnonzero(row):
        if start is None or x - last > GAP_PX + 1:
            start = x
        last = x
        if last - start + 1 > best[0]:
            best = (last - start + 1, start)
    return best


def find_rules(pg: Page) -> list[tuple[float, float, float]]:
    """(y, x1, x2) of each rule in the page's content area."""
    content = [r for r in pg.regions if r.role in ("title", "text", "caption", "figure")]
    if not content:
        return []
    x1, y1 = int(min(r.x1 for r in content)), int(min(r.y1 for r in content))
    x2, y2 = int(max(r.x2 for r in content)), int(max(r.y2 for r in content))
    with Image.open(pg.image_path) as im:
        grey = np.asarray(im.convert("L").crop((x1, y1, x2, y2)), dtype=np.int16)
    ink = grey < np.median(grey) - DARK
    found = []
    for y in range(CLEAR_PX, ink.shape[0] - CLEAR_PX):
        n, s = longest_run(ink[y])
        if n < MIN_LEN_PX or n > MAX_SHARE * (x2 - x1):
            continue
        above = ink[y - CLEAR_PX:y - 2, s:s + n].mean()
        below = ink[y + 3:y + CLEAR_PX + 1, s:s + n].mean()
        if above < CLEAR_INK and below < CLEAR_INK and ink[y, s:s + n].mean() > SOLID:
            found.append((y + y1, s + x1, s + n + x1))
    rules = []
    for y, a, b in found:
        near = next((i for i, (ry, ra, rb) in enumerate(rules)
                     if y - ry <= GROUP_PX and a <= rb + GROUP_GAP_PX and b >= ra - GROUP_GAP_PX), None)
        if near is None:  # (rules level with each other in two columns stay apart)
            rules.append((y, a, b))
        else:
            ry, ra, rb = rules[near]
            rules[near] = (ry, min(ra, a), max(rb, b))
    return rules


def numeric(r: Region) -> bool:
    """A table: many of the box's words are figures."""
    words = r.text.split()
    return bool(words) and sum(any(c.isdigit() for c in w) for w in words) / len(words) >= TABLE_SHARE


def rule_column(pg: Page, rule) -> int | None:
    """The column a rule is centred in, or None."""
    _, a, b = rule
    col = column_of(pg, a, b)
    if col is None:
        return None
    width = column_width(pg)
    centre = pg.text_left + (col - 0.5) * width
    return col if abs((a + b) / 2 - centre) <= CENTRED * width else None


def split_at(pg: Page, r: Region, y: float, n: int) -> Region | None:
    """Split a text box's lines at a rule; the lower part becomes a new box.
    Not when only one line is above it: that's a heading's underline (Chambers
    "BEAR HUNTING." boxed with its text)."""
    upper = [l for l in r.lines if l.cy < y]
    lower = [l for l in r.lines if l.cy >= y]
    if len(upper) < 2 or not lower:
        return None
    bbox = (r.x1, min(l.bbox[1] for l in lower), r.x2, r.y2)
    new = Region(pg.magazine, pg.page, 200 + n, "rule_split", r.score, bbox,
                 role="text", column=r.column, lines=lower,
                 text=join_lines([l.text for l in lower]),
                 note=f"lower part of box {r.index}, split at a printed rule")
    r.lines, r.text = upper, join_lines([l.text for l in upper])
    r.bbox = (r.x1, r.y1, r.x2, max(l.bbox[3] for l in upper))
    pg.regions.append(new)
    return new


def footnote_below(box: Region | None) -> bool:
    """A footnote: its mark opens the box, or OCR scrambled it into the first
    few words ("and * P.S have since observed")."""
    return box is not None and bool(
        FOOTNOTE.match(box.text) or "*" in " ".join(box.text.split()[:3]))


def mark_rules(pg: Page) -> None:
    """Find item rules and mark the boxes they separate (rule_above /
    rule_below); split a text box a rule runs through. The rule above a
    footnote separates nothing: it only marks the footnote (under_rule) (v3,
    decision 1). Runs before reading order is numbered."""
    n_split = 0
    for rule in find_rules(pg):
        y, a, b = rule
        cx = (a + b) / 2
        col = rule_column(pg, rule)
        if col is None:
            continue  # off-centre: a table total, footnote rule, or line in a cut
        in_column = [r for r in pg.regions if (r.column == col or r.x1 < cx < r.x2)
                     and r.role in ("title", "text", "caption", "figure")]
        if any(r.y1 < y < r.y2 for r in in_column if r.role == "figure"):
            continue  # a line in an illustration
        inside = [r for r in in_column if r.role == "text"
                  and r.y1 + EDGE_PX < y < r.y2 - EDGE_PX]
        if inside and numeric(inside[0]):
            continue  # a total line in a table
        if inside:
            box = inside[0]
            new = split_at(pg, box, y, n_split)
            if new:
                n_split += 1
                new.under_rule = True
                if not footnote_below(new):
                    new.rule_above, box.rule_below = True, True
                continue
            if any(l.cy > y for l in box.lines):
                continue  # a heading's underline inside the box
            # below the box's last line: the rule is in the gap after it
        above = max((r for r in in_column if r.y2 <= y + EDGE_PX or r in inside),
                    key=lambda r: r.y2, default=None)
        below = min((r for r in in_column if r.y1 >= y - EDGE_PX and r not in inside),
                    key=lambda r: r.y1, default=None)
        # A box YOLO set aside (abandon) just below the rule: usually a footnote.
        set_aside = [r for r in pg.regions if r.role == "furniture" and r.text
                     and r.x1 < cx < r.x2 and -EDGE_PX <= r.y1 - y <= FOOT_REACH_PX]
        for r in set_aside:
            r.under_rule = True
        if below is not None:
            below.under_rule = True
        if above is None or above.role != "text" or numeric(above):
            continue  # under a title (Chambers' title rules), caption, figure or table
        if any(footnote_below(r) for r in set_aside) or (
                below is not None and below.role == "text" and footnote_below(below)):
            continue  # a footnote's rule
        above.rule_below = True
        if below is not None and below.role == "text":
            below.rule_above = True
