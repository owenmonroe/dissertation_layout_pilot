"""Page layout from DocLayout-YOLO output.

Loads one page's YOLO boxes, removes overlapping duplicates, gives every box a
role (title / text / figure / caption / masthead / furniture), assigns it to a
text column, and puts the content boxes in reading order:

  - the page is cut into horizontal bands at boxes that span columns (e.g. an
    illustration across both columns);
  - within a band, left column top-to-bottom, then the next column, and so on;
  - a spanning box is read between the band above it and the band below it.

Box indexes are the YOLO JSON "regions" positions, i.e. the #N on the eval
images in evaluation/output_eval/<mag>_yolo_eval/.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

# Text columns per page.
COLUMNS = {"penny": 2, "saturday": 2, "chambers": 3}
# Drop a box when at least this share of it is covered by higher-scoring boxes
# (YOLO duplicates, and low-score boxes stretched over several real ones).
OVERLAP_DROP = 0.8
# A box spans columns when it covers at least this share of 2+ columns' width.
SPAN_SHARE = 0.2
# Issue-start pages have a spanning masthead box in this top share of the page.
MASTHEAD_TOP = 0.12
# Masthead ends at the first full paragraph (taller than this) ...
MIN_PARAGRAPH_PX = 120
# ... or the first column title at least this share of a column wide (not a
# tiny "[1.]" issue-number box).
MIN_TITLE_SHARE = 0.25

YOLO_ROLES = {
    "title": "title",
    "plain text": "text",
    "abandon": "furniture",
    "figure": "figure",
    "figure_caption": "caption",
    "table_caption": "caption",
    "table_footnote": "caption",
    "formula_caption": "caption",
}
CONTENT_ROLES = {"title", "text", "figure", "caption"}


@dataclass
class Region:
    magazine: str
    page: int
    index: int
    yolo_type: str
    score: float
    bbox: tuple
    role: str = ""
    column: int | None = None  # 1-based; None = spans columns
    band: int = 0
    order: int | None = None  # reading order among content boxes, 1-based
    lines: list = field(default_factory=list)
    text: str = ""
    caption: str = ""
    note: str = ""

    @property
    def region_id(self) -> str:
        return f"{self.magazine}_p{self.page:03d}_r{self.index:02d}"

    @property
    def x1(self): return self.bbox[0]
    @property
    def y1(self): return self.bbox[1]
    @property
    def x2(self): return self.bbox[2]
    @property
    def y2(self): return self.bbox[3]
    @property
    def cx(self): return (self.x1 + self.x2) / 2
    @property
    def cy(self): return (self.y1 + self.y2) / 2
    @property
    def area(self): return max(self.x2 - self.x1, 0) * max(self.y2 - self.y1, 0)


@dataclass
class Page:
    magazine: str
    page: int
    image_path: Path
    width: int
    height: int
    regions: list
    issue_start: bool = False
    text_left: float = 0
    text_right: float = 0

    @property
    def ordered(self) -> list:
        return sorted((r for r in self.regions if r.order), key=lambda r: r.order)


def intersection(a: Region, b: Region) -> float:
    w = min(a.x2, b.x2) - max(a.x1, b.x1)
    h = min(a.y2, b.y2) - max(a.y1, b.y1)
    return w * h if w > 0 and h > 0 else 0


def yolo_json_path(magazine: str, page: int) -> Path:
    return (REPO_ROOT / "output" / f"{magazine}_yolo" / f"json_bounding_{magazine}_yolo"
            / f"{magazine}_page_{page:03d}_doclayoutyolo.json")


def load_page(magazine: str, page: int) -> Page:
    from PIL import Image

    data = json.loads(yolo_json_path(magazine, page).read_text())
    image_path = Path(data["page_image"])
    with Image.open(image_path) as im:
        width, height = im.size
    regions = [
        Region(magazine, page, i, r["type"], r["score"], tuple(r["bbox"]))
        for i, r in enumerate(data["regions"])
    ]
    pg = Page(magazine, page, image_path, width, height, regions)
    drop_overlaps(pg)
    assign_roles(pg)
    assign_columns(pg)
    mark_masthead(pg)
    return pg


def drop_overlaps(pg: Page) -> None:
    kept = []
    for r in sorted(pg.regions, key=lambda r: -r.score):
        covering = [k for k in kept if intersection(r, k)]
        covered = sum(intersection(r, k) for k in covering) / r.area if r.area else 1
        if covered >= OVERLAP_DROP:
            r.role = "dropped"
            r.note = "covered by " + ", ".join(f"#{k.index}" for k in covering)
        else:
            kept.append(r)


def assign_roles(pg: Page) -> None:
    for r in pg.regions:
        if r.role != "dropped":
            r.role = YOLO_ROLES.get(r.yolo_type, "text")


def assign_columns(pg: Page) -> None:
    text = [r for r in pg.regions if r.role == "text"] or \
           [r for r in pg.regions if r.role in CONTENT_ROLES]
    if not text:
        return
    pg.text_left = min(r.x1 for r in text)
    pg.text_right = max(r.x2 for r in text)
    for r in pg.regions:
        if r.role in CONTENT_ROLES:
            r.column = column_of(pg, r.x1, r.x2)


def column_width(pg: Page) -> float:
    return (pg.text_right - pg.text_left) / COLUMNS[pg.magazine]


def column_of(pg: Page, x1: float, x2: float) -> int | None:
    """1-based column a span x1..x2 sits in, or None if it spans columns."""
    col_w = column_width(pg)
    overlaps = []
    for c in range(COLUMNS[pg.magazine]):
        left = pg.text_left + c * col_w
        overlaps.append(max(0, min(x2, left + col_w) - max(x1, left)))
    if sum(o >= SPAN_SHARE * col_w for o in overlaps) >= 2:
        return None
    return overlaps.index(max(overlaps)) + 1


def mark_masthead(pg: Page) -> None:
    """On an issue's first page, the boxes at the top before the first article.

    An issue-start page has a spanning box near the top (the magazine's name).
    Reading down from the top, boxes are masthead (name, society, "published
    every Saturday", date, issue number) until the first thing that belongs to
    an article: a column-width title, a figure, or a full paragraph of text.
    """
    content = [r for r in pg.regions if r.role in CONTENT_ROLES]
    pg.issue_start = any(
        r.column is None and r.role in ("title", "text") and r.y1 < MASTHEAD_TOP * pg.height
        for r in content
    )
    if not pg.issue_start:
        return
    for r in sorted(content, key=lambda r: r.y1):
        article_starts = (
            (r.role == "title" and r.column is not None
             and r.x2 - r.x1 >= MIN_TITLE_SHARE * column_width(pg))
            or r.role == "figure"
            or (r.role == "text" and r.y2 - r.y1 >= MIN_PARAGRAPH_PX)
        )
        if article_starts:
            break
        r.role = "masthead"


def order_regions(pg: Page) -> None:
    content = [r for r in pg.regions if r.role in CONTENT_ROLES]
    spanning = sorted((r for r in content if r.column is None), key=lambda r: r.cy)
    for r in content:
        r.band = sum(s.cy < r.cy for s in spanning) if r.column else spanning.index(r)
    order = 1
    for band in range(len(spanning) + 1):
        for col in range(1, COLUMNS[pg.magazine] + 1):
            for r in sorted((r for r in content if r.column == col and r.band == band),
                            key=lambda r: r.cy):
                r.order, order = order, order + 1
        if band < len(spanning):
            spanning[band].order, order = order, order + 1
