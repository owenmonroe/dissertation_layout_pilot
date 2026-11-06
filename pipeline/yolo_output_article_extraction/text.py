"""Text for each YOLO box.

Default ("docai"): reuse the Document AI OCR already in
output/output_images_json_establishing_layout_AIs/<mag>_google/json_bounding_<mag>_google/. Each OCR word (token) is
assigned to the YOLO box containing its centre, so YOLO decides the layout and
Document AI supplies the text. Words keep Document AI's own line grouping and
word order; a line is only split where it crosses from one box into another
(its lines can run straight across both columns). Words no box contains are attached to a box directly above/below
them if within NEAR_PX (YOLO boxes that stop a line short), otherwise reported
as "unboxed". Unboxed lines that form a block in a column (text YOLO drew no
box for at all) become new text regions; see recover_unboxed.
A line of capitals YOLO boxed with nothing, or swallowed at the top of a paragraph
box, becomes a heading of its own (recover_unboxed, split_headings).

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
from magazine_rules_config import VOLUMES, magazine_rules

PAD_PX = 6  # tolerance when testing whether a line centre is inside a box
NEAR_PX = 30
SENTENCE_END = re.compile(r"[.!?:;\"”’)\]]$")
# The scan's own stamps (HathiTrust / Google): never text.
WATERMARK = re.compile(r"hdl\.handle\.net|google-digitized|public domain|digitized by|"
                       r"generated at|original from|\b\d\d:\d\d GMT\b", re.I)
# A footnote's opening mark. OCR often reads the asterisk as "•" or "+" (v4,
# rule 4: 5 of 5 such boxes in nine volumes are footnotes); never a full stop.
# "§" with a number opens a section heading, not a footnote ("§ 6. On the
# Form and Language of Wills.").
FOOTNOTE = re.compile(r"^\s*(?:[*†‡•+]|§(?!\s*\d))")
# A box YOLO set aside (abandon) that is really content (v3, decision 3):
# enough words, inside the text area, in the page's body type.
CONTENT_MIN_WORDS = 12
CONTENT_TOP, CONTENT_BOTTOM = 0.08, 0.95  # share of page height
SMALL_TYPE = 0.85  # line height against the body's: footnotes and imprints are smaller
# Column rules OCR'd as characters.
RULE_CHARS = {"|", "I", "l", "❘", "/", "¦"}
# A recovered block with about one word per line is a strip of line-end (or
# line-start) words cut off a box by page tilt, not a paragraph: real
# paragraphs run 2.5+ words a line on the development pages, strips 1.0.
STRIP_WORDS_PER_LINE = 1.5
STRIP_MAX_WIDTH = 0.15  # share of the column width
SIDE_GAP_PX = 30  # a strip or line this close to a box's side belongs to that box
REJOIN_MIN_LINES = 3  # only paragraph boxes take rejoined words ("12" + "EDINBURGHSHIRE." isn't one)
REJOIN_BELOW = 0.15  # share of page height: above it (masthead, running head) nothing is rejoined
# A heading YOLO drew no box for (v3, decision 5): an all-capitals line alone
# between boxes, or centred at the top of a paragraph box.
HEADING_MIN_WORDS = 2
HEADING_INSET = 0.08  # share of the box's width left free on each side: centred
TABLE_DIGITS = 0.15  # share of a box's characters
# A capitals line with no box, within this many px of a figure's side and
# level with it, is the figure's caption (v4).
CAPTION_GAP_PX = 60
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
    return (REPO_ROOT / VOLUMES[magazine].model_output_dir / f"{magazine}_google" / f"json_bounding_{magazine}_google"
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


def capitals_line(line: Line) -> bool:
    return line.text.isupper() and len(line.text.split()) >= HEADING_MIN_WORDS


def beside_figure(pg: Page, line: Line) -> bool:
    """A line inside a figure's box or right beside it, level with it (a
    caption printed sideways along a full-page picture: Saturday 1834 p5)."""
    x1, y1, x2, y2 = line.bbox
    for f in (r for r in pg.regions if r.role == "figure"):
        if f.y1 <= line.cy <= f.y2 and f.x1 - CAPTION_GAP_PX <= x1 and x2 <= f.x2 + CAPTION_GAP_PX:
            return True
    return False


def heading_region(pg: Page, line: Line, column, index: int, note: str) -> Region:
    return Region(pg.magazine, pg.page, index, "unboxed_ocr", 0.0, line.bbox, role="title",
                  column=column, lines=[line], text=line.text, note=note)


def split_headings(pg: Page) -> None:
    """A centred line of capitals opening a paragraph box is a heading the box
    swallowed ("STORY FROM THE CAUSES CELEBRES."): it becomes its own box."""
    for n, r in enumerate([r for r in pg.regions if r.role == "text"]):
        digits = sum(c.isdigit() for c in r.text) / max(len(r.text), 1)
        if len(r.lines) < REJOIN_MIN_LINES or r.lines[0].cy < REJOIN_BELOW * pg.height \
                or digits > TABLE_DIGITS:
            continue  # a table's heading stays with its table
        line, inset = r.lines[0], HEADING_INSET * (r.x2 - r.x1)
        if capitals_line(line) and line.bbox[0] >= r.x1 + inset and line.bbox[2] <= r.x2 - inset:
            pg.regions.append(heading_region(pg, line, r.column, 200 + n, "heading split from a text box"))
            r.lines = r.lines[1:]
            r.text = join_lines([l.text for l in r.lines])
            r.bbox = (r.x1, max(r.y1, line.bbox[3]), r.x2, r.y2)


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
        for l in [l for l in col_lines if capitals_line(l) and l.cy >= REJOIN_BELOW * pg.height]:
            # before grouping: stray line-end words nearby would swallow it
            if beside_figure(pg, l):  # a picture's caption, never a title (v4)
                pg.regions.append(Region(pg.magazine, pg.page, 100 + new, "unboxed_ocr", 0.0, l.bbox,
                                         role="caption", column=col, lines=[l], text=l.text,
                                         note="caption beside a figure with no YOLO box"))
            else:
                pg.regions.append(heading_region(pg, l, col, 100 + new, "heading line with no YOLO box"))
            new += 1
            col_lines.remove(l)
        if not col_lines:
            continue
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


def type_size(pg: Page, r: Region) -> float:
    """Box r's line height against the page's body text (1.0 = body type)."""
    body = sorted(l.bbox[3] - l.bbox[1] for b in pg.regions if b.role == "text"
                  and len(b.lines) >= 5 for l in b.lines)
    mine = sorted(l.bbox[3] - l.bbox[1] for l in r.lines)
    return mine[len(mine) // 2] / body[len(body) // 2] if body and mine else 1.0


# A footnote YOLO boxed with the paragraph above it (v4, rule 5): from a line
# opening with a mark and a capital ("* Nahum, ch. i. v. 8."), in smaller type
# than the lines above, to the end of the box, no more than a few lines.
# (A footnote with its mark lost is not looked for by place: at the foot of a
# column it reads like any last paragraph, poem or notice; v4, rule 5 tested.)
FOOTNOTE_LINE = re.compile(r"^\s*[*†‡•+]{1,2}\s*[\"'‘“]?[A-Z]")
FOOTNOTE_TAIL_TYPE = 0.92  # its line height against the lines above
FOOTNOTE_TAIL_LINES = 8
FOOTNOTE_TAIL_ABOVE = 3  # lines of paragraph above it at least ("JOHN STOUPIE, Clerk." / "* AIR, ..." is a play)


def median_height(lines) -> float:
    h = sorted(l.bbox[3] - l.bbox[1] for l in lines)
    return h[len(h) // 2]


def split_footnote_tails(pg: Page) -> None:
    """Cut a footnote off the foot of the text box it was boxed with: it
    becomes a box of its own, read as a footnote (back matter of the article
    it annotates). The paragraph above is not changed."""
    for n, r in enumerate([r for r in pg.regions if r.role == "text"]):
        for k in range(FOOTNOTE_TAIL_ABOVE, len(r.lines)):
            tail = r.lines[k:]
            if not FOOTNOTE_LINE.match(r.lines[k].text) or len(tail) > FOOTNOTE_TAIL_LINES:
                continue
            if median_height(tail) >= FOOTNOTE_TAIL_TYPE * median_height(r.lines[:k]):
                continue
            bbox = (min(l.bbox[0] for l in tail), tail[0].bbox[1], max(l.bbox[2] for l in tail),
                    max(l.bbox[3] for l in tail))
            pg.regions.append(Region(pg.magazine, pg.page, 400 + n, r.yolo_type, r.score, bbox,
                                     role="text", column=r.column, lines=tail,
                                     text=join_lines([l.text for l in tail]),
                                     note="footnote cut from the foot of a text box (mark, smaller type)"))
            r.lines = r.lines[:k]
            r.text = join_lines([l.text for l in r.lines])
            r.bbox = (r.x1, r.y1, r.x2, min(r.y2, tail[0].bbox[1]))
            break


def promote_content(pg: Page) -> None:
    """Content YOLO labelled abandon, such as a poem with no title, comes back
    as text. Footnotes (a mark, or small type) and imprints stay set aside."""
    imprint = magazine_rules(pg.magazine).imprint
    for r in pg.regions:
        if r.role != "furniture" or len(r.text.split()) < CONTENT_MIN_WORDS:
            continue
        if not (CONTENT_TOP * pg.height <= r.y1 and r.y2 <= CONTENT_BOTTOM * pg.height) \
                or column_of(pg, r.x1, r.x2) is None or WATERMARK.search(r.text) \
                or FOOTNOTE.match(r.text) or imprint.search(r.text):
            continue
        if type_size(pg, r) >= SMALL_TYPE:
            r.role, r.column = "text", column_of(pg, r.x1, r.x2)
            r.note = "content YOLO set aside (abandon): read as text"


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
    boxes = [r for r in boxes if len(r.lines) >= REJOIN_MIN_LINES]  # paragraphs, not headings
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
