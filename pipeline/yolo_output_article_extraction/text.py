"""Text for each YOLO box.

Default ("docai"): reuse the Document AI OCR already in
output/<mag>_google/json_bounding_<mag>_google/. Each OCR word (token) is
assigned to the YOLO box containing its centre, so YOLO decides the layout and
Document AI supplies the text. Words keep Document AI's own line grouping and
word order; a line is only split where it crosses from one box into another
(its lines can run straight across both columns). Words no box contains are attached to a box directly above/below
them if within NEAR_PX (YOLO boxes that stop a line short), otherwise reported
as "unboxed". Unboxed lines that form a block in a column (text YOLO drew no
box for at all) become new text regions; see recover_unboxed.

Fallback ("tesseract"): OCR each box crop locally with the tesseract CLI.
"""

import bisect
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from layout import CONTENT_ROLES, REPO_ROOT, Page, Region, column_of

PAD_PX = 6  # tolerance when testing whether a line centre is inside a box
NEAR_PX = 30
SENTENCE_END = re.compile(r"[.!?:;\"”’)\]]$")
# The scan's own stamps (HathiTrust / Google): never text.
WATERMARK = re.compile(r"hdl\.handle\.net|google-digitized|public domain|digitized by|"
                       r"generated at|original from|\b\d\d:\d\d GMT\b", re.I)
# Column rules OCR'd as characters.
RULE_CHARS = {"|", "I", "l", "❘", "/", "¦"}
# A recovered block with about one word per line is a strip of line-end (or
# line-start) words cut off a box by page tilt, not a paragraph: real
# paragraphs run 2.5+ words a line on the development pages, strips 1.0.
STRIP_WORDS_PER_LINE = 1.5
STRIP_MAX_WIDTH = 0.15  # share of the column width
SIDE_GAP_PX = 30  # a strip or line this close to a box's side belongs to that box
REJOIN_BELOW = 0.15  # share of page height: above it (masthead, running head) nothing is rejoined
# Printer's marks caught in a text box: a signature or volume mark after the
# last sentence ("... perfection. VOL. I.", "... crime. 3-2", "... sea. C").
TRAILING_MARK = re.compile(r"(?<=[.!?\"”’:;])\s+(?:VOL\.?\s*[IVX]+\.?|[A-Z]|\d{1,2}(?:-\d{1,2})?|[A-Z]\s?\d)\s*$")
VOLUME_MARK = re.compile(r"\s+VOL\.?\s*[IVX]+\.?\s*$")  # anywhere at a box's end: "... The VOL. I."
LEADING_MARK = re.compile(r"^\s*0\d\s+(?=[a-z])")  # "02 of the heroine"
# An opening quotation mark OCR'd as "44" or "66": "44 When he was about ..."
QUOTE_DIGITS = re.compile(r"(?:(?<=^)|(?<=\s))(?:44|66)\s+(?=[A-Z])")


@dataclass
class Line:
    text: str
    bbox: tuple
    line_no: int = 0  # Document AI line the word belongs to
    start: int = 0  # offset in Document AI's text = its word order

    @property
    def cx(self): return (self.bbox[0] + self.bbox[2]) / 2
    @property
    def cy(self): return (self.bbox[1] + self.bbox[3]) / 2


def docai_json_path(magazine: str, page: int) -> Path:
    return (REPO_ROOT / "output" / f"{magazine}_google" / f"json_bounding_{magazine}_google"
            / f"{magazine}_page_{page:03d}_docai.json")


def docai_tokens(pg: Page) -> list[Line]:
    """Document AI words, each with its own trailing space / newline."""
    doc = json.loads(docai_json_path(pg.magazine, pg.page).read_text())
    page = doc["pages"][0]
    sx = pg.width / page["dimension"]["width"]
    sy = pg.height / page["dimension"]["height"]
    line_starts = sorted(
        int(line["layout"]["textAnchor"]["textSegments"][0].get("startIndex", 0))
        for line in page["lines"]
    )
    tokens = []
    for token in page["tokens"]:
        layout = token["layout"]
        segments = layout["textAnchor"]["textSegments"]
        start = int(segments[0].get("startIndex", 0))
        text = "".join(
            doc["text"][int(s.get("startIndex", 0)):int(s["endIndex"])] for s in segments
        ).replace("\n", " ")
        xs = [v.get("x", 0) * sx for v in layout["boundingPoly"]["vertices"]]
        ys = [v.get("y", 0) * sy for v in layout["boundingPoly"]["vertices"]]
        if text.strip():
            tokens.append(Line(text, (min(xs), min(ys), max(xs), max(ys)),
                               bisect.bisect_right(line_starts, start), start))
    return tokens


def contains(r, token: Line, pad: float = PAD_PX) -> bool:
    return r.x1 - pad <= token.cx <= r.x2 + pad and r.y1 - pad <= token.cy <= r.y2 + pad


def group_lines(tokens: list[Line]) -> list[Line]:
    """Words back into Document AI's lines (word order kept), lines top to bottom."""
    rows = {}
    for t in tokens:
        rows.setdefault(t.line_no, []).append(t)
    lines = []
    for row in rows.values():
        row.sort(key=lambda t: t.start)
        lines.append(Line("".join(t.text for t in row).strip(),
                          (min(t.bbox[0] for t in row), min(t.bbox[1] for t in row),
                           max(t.bbox[2] for t in row), max(t.bbox[3] for t in row))))
    return sorted(lines, key=lambda l: l.cy)


def assign_docai_text(pg: Page) -> list[Line]:
    """Fill region.lines / region.text from Document AI. Returns unboxed lines."""
    boxes = [r for r in pg.regions if r.role in CONTENT_ROLES | {"furniture", "masthead"}]
    content = [r for r in boxes if r.role in ("title", "text", "caption")]
    words = {r.region_id: [] for r in boxes}
    unboxed = []
    for token in docai_tokens(pg):
        hits = [r for r in boxes if contains(r, token)]
        if hits:
            words[min(hits, key=lambda r: r.area).region_id].append(token)
            continue
        near = [r for r in content if r.x1 <= token.cx <= r.x2
                and min(abs(token.cy - r.y1), abs(token.cy - r.y2)) <= NEAR_PX]
        if near:
            r = min(near, key=lambda r: min(abs(token.cy - r.y1), abs(token.cy - r.y2)))
            words[r.region_id].append(token)
            if "words attached" not in r.note:
                r.note = (r.note + "; " if r.note else "") + "words attached from just outside box"
        elif token.text.strip() not in RULE_CHARS:  # column rules read as characters
            unboxed.append(token)
    for r in boxes:
        r.lines = group_lines(words[r.region_id])
        r.text = join_lines([l.text for l in r.lines])
    return group_lines(unboxed)


def recover_unboxed(pg: Page, lines: list[Line]) -> list[Line]:
    """Turn blocks of unboxed lines into text regions; return lines still unboxed.

    Lines are split by column, then consecutive lines no more than ~1.5 line
    heights apart form a block. Blocks above the content or below it (scan
    watermark) are left out, as are single lines. Runs before the masthead is
    marked, so masthead lines YOLO missed are recovered and then marked too.
    """
    content = [r for r in pg.regions if r.role in ("title", "text", "figure", "caption")]
    if not content or not lines:
        return lines
    top = min(r.y1 for r in content)
    bottom = max(r.y2 for r in content)
    leftover, blocks = [], {}
    text_boxes = [r for r in content if r.role == "text"]
    for line in lines:
        if WATERMARK.search(line.text):
            leftover.append(line)
            continue
        col = column_of(pg, line.bbox[0], line.bbox[2])
        if col is None or not (top - 10 <= line.cy <= bottom + 20):
            leftover.append(line)
        else:
            blocks.setdefault(col, []).append(line)
    new = 0
    for col, col_lines in blocks.items():
        col_lines.sort(key=lambda l: l.cy)
        height = sorted(l.bbox[3] - l.bbox[1] for l in col_lines)[len(col_lines) // 2]
        groups = [[col_lines[0]]]
        for l in col_lines[1:]:
            if l.cy - groups[-1][-1].cy <= 1.5 * height * 1.6:
                groups[-1].append(l)
            else:
                groups.append([l])
        width = (pg.text_right - pg.text_left) / max(1, len({r.column for r in content if r.column}))
        for g in groups:
            if len(g) < 2:
                if g[0].cy < REJOIN_BELOW * pg.height or not rejoin(g, text_boxes):
                    leftover.extend(g)
                continue
            words_per_line = sum(len(l.text.split()) for l in g) / len(g)
            if words_per_line <= STRIP_WORDS_PER_LINE:
                narrow = max(l.bbox[2] for l in g) - min(l.bbox[0] for l in g) <= STRIP_MAX_WIDTH * width
                if not (narrow and g[0].cy >= REJOIN_BELOW * pg.height and rejoin(g, text_boxes)):
                    leftover.extend(g)  # junk: "10 кат his this rith hat", "Is an"
                continue
            bbox = (min(l.bbox[0] for l in g), min(l.bbox[1] for l in g),
                    max(l.bbox[2] for l in g), max(l.bbox[3] for l in g))
            r = Region(pg.magazine, pg.page, 100 + new, "unboxed_ocr", 0.0, bbox,
                       role="text", column=col, lines=g, text=join_lines([l.text for l in g]),
                       note="text Document AI read where YOLO drew no box")
            pg.regions.append(r)
            new += 1
    return leftover


def drop_empty(pg: Page) -> None:
    """A title/text/caption box that got no OCR words at all is empty, or a
    duplicate of a box that got the words (each word goes to one box); drop it
    before reading order is numbered."""
    for r in pg.regions:
        if r.role in ("title", "text", "caption") and not r.text.strip():
            r.role, r.note = "dropped", "no OCR words: empty box, or a duplicate of one that got them"


def assign_tesseract_text(pg: Page) -> list[Line]:
    from PIL import Image

    with Image.open(pg.image_path) as im, tempfile.TemporaryDirectory() as tmp:
        crop_path = Path(tmp) / "crop.png"
        for r in pg.regions:
            if r.role not in CONTENT_ROLES | {"furniture", "masthead"} or r.role == "figure":
                continue
            im.crop((r.x1 - PAD_PX, r.y1 - PAD_PX, r.x2 + PAD_PX, r.y2 + PAD_PX)).save(crop_path)
            psm = "7" if r.y2 - r.y1 < 80 else "6"  # one line vs a block
            out = subprocess.run(["tesseract", str(crop_path), "stdout", "--psm", psm],
                                 capture_output=True).stdout.decode("utf-8", "replace")
            r.text = join_lines([l.strip() for l in out.splitlines() if l.strip()])
    return []


def rejoin(lines: list[Line], boxes: list[Region]) -> bool:
    """Put lines YOLO's box missed back into that box (decision 8): a strip
    of words just past a box's side goes onto the box's lines at the same
    height (end or start of the line); a line just above or below a box in
    its column becomes the box's first or last line. False if no box is near."""
    x1, x2 = min(l.bbox[0] for l in lines), max(l.bbox[2] for l in lines)
    y1, y2 = min(l.bbox[1] for l in lines), max(l.bbox[3] for l in lines)
    height = max(l.bbox[3] - l.bbox[1] for l in lines)
    beside = [r for r in boxes if r.lines and r.y1 - height <= (y1 + y2) / 2 <= r.y2 + height
              and (r.x2 - SIDE_GAP_PX <= x1 <= r.x2 + SIDE_GAP_PX       # just past its right edge
                   or r.x1 - SIDE_GAP_PX <= x2 <= r.x1 + SIDE_GAP_PX)]  # or its left edge
    if beside:
        box = beside[0]
        right = x1 >= box.cx
        for l in lines:
            target = min(box.lines, key=lambda bl: abs(bl.cy - l.cy))
            if abs(target.cy - l.cy) > height:
                return False
        for l in lines:
            target = min(box.lines, key=lambda bl: abs(bl.cy - l.cy))
            target.text = f"{target.text} {l.text}" if right else f"{l.text} {target.text}"
        box.text = join_lines([bl.text for bl in box.lines])
        box.note = (box.note + "; " if box.note else "") + "line-end words past the box's side rejoined"
        return True
    if len(lines) == 1:
        l = lines[0]
        near = [r for r in boxes if r.lines and r.x1 - SIDE_GAP_PX <= l.cx <= r.x2 + SIDE_GAP_PX
                and min(abs(l.bbox[1] - r.y2), abs(r.y1 - l.bbox[3])) <= 1.5 * height]
        if near:
            box = min(near, key=lambda r: min(abs(l.bbox[1] - r.y2), abs(r.y1 - l.bbox[3])))
            box.lines = sorted(box.lines + [l], key=lambda bl: bl.cy)
            box.text = join_lines([bl.text for bl in box.lines])
            box.bbox = (box.x1, min(box.y1, l.bbox[1]), box.x2, max(box.y2, l.bbox[3]))
            box.note = (box.note + "; " if box.note else "") + "line just outside the box recovered"
            return True
    return False


def clean_marks(pg: Page) -> None:
    """Printer's marks and OCR'd quotation marks in text boxes (decision 8)."""
    for r in pg.regions:
        if r.role != "text" or not r.text:
            continue
        text = TRAILING_MARK.sub("", VOLUME_MARK.sub("", r.text))
        text = LEADING_MARK.sub("", text)
        text = QUOTE_DIGITS.sub("\u201c", text)
        if text != r.text:
            r.text = text
            r.note = (r.note + "; " if r.note else "") + "printer's mark / OCR'd quote cleaned"


def join_lines(lines: list[str]) -> str:
    """Join OCR lines into running text, undoing end-of-line hyphenation."""
    out = ""
    for line in lines:
        if not out:
            out = line
        elif out.endswith("-") and line[:1].islower():
            out = out[:-1] + line
        else:
            out += " " + line
    return out


def join_regions(texts: list[str]) -> str:
    """Join box texts into an article: paragraph break between boxes, unless the
    previous box stops mid-sentence (a paragraph running on into the next
    column or page)."""
    out = ""
    for t in texts:
        if not t:
            continue
        if not out:
            out = t
        elif SENTENCE_END.search(out):
            out += "\n\n" + t
        else:
            out = join_lines([out, t])
    return out
