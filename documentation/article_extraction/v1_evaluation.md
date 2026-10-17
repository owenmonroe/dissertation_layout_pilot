# Article Extraction — v1 Evaluation (Reading Order and Article Assignment)

## Purpose

Hand-evaluation of the article-extraction pipeline
(`pipeline/yolo_output_article_extraction/`, v1 rules in `v1_rules.md`, code
tag `extraction-v1`):
for every box it placed, is the box in the right reading order, the right
article and the right role? This is the second evaluation after the box study
(`../evaluation_error_log_documentation.md`), with matching error types where
possible.

Two rounds:

- **Development (now):** the 74 sample pages (penny 26, Saturday 24, Chambers
  24). Rules were tuned on these pages, so the results guide fixes; they are
  not the reported accuracy.
- **Test (later):** fresh later-year issues, evaluated once with the pipeline
  frozen; those numbers are the baseline.

OCR word accuracy is evaluated separately (WER/CER against a literal
transcription); OCR noise in a box is not an error here.

## Files

- `evaluation/make_reading_order_template.py` builds the log from the
  pipeline's CSVs in `output/article_extraction/<mag>/`. It refuses to
  overwrite an existing log unless run with `--force`.
- `evaluation/reading_order_error_log.csv` is the log.
- The check images are in
  `output/article_extraction/<mag>/reading_order/<mag>_page_NNN_order.jpg`.
  Each box is labelled `<reading order> · <article>`, matching the log's
  `reading_order` and `article` columns. Grey boxes are masthead, furniture
  or dropped.

## The log

One row per box the pipeline placed: every box in a page's reading order, plus
masthead boxes, since a box wrongly taken as masthead loses article text.
Headers, page numbers, margins and dropped duplicate boxes are left out.

| Column | Meaning |
|---|---|
| `magazine`, `page`, `printed_page`, `issue_no`, `issue_date` | where the box is, and the metadata the pipeline found |
| `reading_order` | position in the page's reading order (empty for masthead) |
| `region_id`, `yolo_index` | the box (`yolo_index` = YOLO's #N on the box-study eval images) |
| `column` | left / right (left / middle / right for Chambers), or spanning |
| `role` | title, text, figure, caption, byline, attribution, end_note, imprint, masthead |
| `article`, `article_id`, `article_title` | the article the box was put in (`article` = the number on the check image) |
| `box_start`, `box_end` | the box's first and last few words |
| `verdict` | pre-filled `ok`; `error` for a wrong box; `excluded` for boxes not evaluated (e.g. duplicate scan pages, penny PDF pp. 22–23) |
| `error_type` | see below (several joined with `; `) |
| `notes` | free text |

### Error types

- `order`: the box is read out of sequence.
- `split`: an article is wrongly broken in two. Logged on the first box of
  the wrongly started article.
- `merge`: two articles are wrongly joined. Logged on the first box of the
  article that should have started.
- `misattached`: the box is put in the wrong article (e.g. a title attached
  to the previous article).
- `role`: wrong role (title / text / caption / byline / attribution /
  masthead / imprint confused).
- `missed`: text lost: the box is missing some of its text, or text on the
  page is in no box. Logged on the nearest box, with a note.
- `metadata`: issue number, date or printed page wrong. Logged on the page's
  first row.
- `misplacement`: a box that cuts across the text, e.g. a vertical strip of
  line-end words cut from a column's edge, so its text can't be read in any
  order (term from the box study).

### Conventions

- Only errors are changed; every other row stays `ok`.
- Several errors on one box go in one row, joined with `; `, in a fixed order
  (as in the box study).
- An article boundary error is logged once, where the boundary should be (or
  wrongly is), not on every box of the article.
- Text-level observations go in `notes` with a `text:` prefix and aren't
  counted. This covers words swapped between neighbouring boxes by page tilt,
  stray furniture words ("OL.I."), scrambled tilted lines, and table OCR.
  These feed the automatic completeness check and the pipeline's text fixes.
- `metadata` is logged only when something printed was missed or misread. A
  page with no printed page number correctly has none.
- A caption or title included inside a figure box is a `role` error, even if
  the pipeline recovers the title from the figure's text.
- A box the log leaves out (furniture) that is really content, e.g. an
  asterisked footnote giving an article's source, gets a row added during
  the evaluation, with a `role` error. Proposed new role: `footnote`, stored
  with the article like `byline` / `attribution`.
- **Recurring features (series)**: e.g. "BRITISH ANIMALS." over the Dormouse
  and the Swallow; "THE WEEK"; "BIOGRAPHIC SKETCHES"; "Column for the Boys".
  - Each piece under the heading is its own article row, with a shared
    `series` label.
  - A series heading taken as a title (or as text) is a `role` error on the
    heading box.
- **Front and back matter** (agreed 2026-10-15). Source lines, epigraphs and
  continuation notes before the text are front matter; sign-offs, footnotes
  and "[To be continued.]" after it are back matter. Where they sit varies,
  so position, not kind, decides.
  - A front/back-matter box read as article text, boxed as a title, or set
    aside as furniture is a `role` error.
  - A sign-off inside a paragraph box (e.g. "…mass. Everett's Essay.") can't
    be a box error; it's a `text:` note.
- **Continuations across issues** ("[Concluded from our last.]") are not
  series. Each part is its own row, later linked by `continues_article_id`.
  A continuation note read as article text is a `role` error (it belongs with
  the title).

## Workflow

Page by page, with Claude Code. For each page, Claude lists the boxes in
reading order (number, column, role, article, first words). Owen compares
them with the check image and replies `ok` or names the errors by reading-order
number. Claude records them in the log. Order: penny → Saturday → Chambers,
page 1 onward.

## Results (development set, complete 2026-10-16)

Template built 2026-10-14 (1,086 boxes); 4 rows were added during the
evaluation for content YOLO had set aside as furniture (footnotes, "[To be
continued.]"), giving 1,090 rows. Penny PDF pp. 22–23 (22 rows) are excluded
as duplicate scan pages, so **1,068 boxes were evaluated**.

| | Penny | Saturday | Chambers | All |
|---|---|---|---|---|
| Boxes evaluated | 313 | 339 | 416 | 1,068 |
| Correct | 280 (89.5%) | 314 (92.6%) | 377 (90.6%) | **971 (90.9%)** |

Errors by type (a box with two errors counts in both rows):

| Error | Penny | Saturday | Chambers | All |
|---|---|---|---|---|
| `role` | 15 | 23 | 25 | 63 |
| `merge` | 16 | 1 | 5 | 22 |
| `misplacement` | 0 | 0 | 8 | 8 |
| `split` | 2 | 0 | 1 | 3 |
| `misattached` | 0 | 1 | 1 | 2 |
| `missed` | 0 | 0 | 1 | 1 |
| `metadata` | 0 | 0 | 0 | 0 |
| `order` | 0 | 0 | 0 | **0** |

### Findings

1. **Reading order works.** No order errors on any page, including Chambers'
   three columns and pages split by full-width illustrations.
2. **Role errors are two-thirds of all errors,** and nearly all involve front
   or back matter: source lines, bylines, epigraphs, footnotes, sign-offs,
   continuation notes, series headings. They're read as text, boxed as titles,
   or set aside as furniture. This led to the front/back-matter design
   (`v2_decisions.md`).
3. **Merges are mostly items with no marker.** 16 of 22 are penny's
   one-paragraph fillers, which appear mid-issue and at issue ends, and some
   run to several paragraphs. The rest are run-in heads the rules missed
   (Chambers "VATICAN", "VEGETABLES", the Africa hunt).
4. **Page tilt (Chambers) causes misplacements:** vertical strips of line-end
   words that the unboxed-text recovery turned into boxes (pp. 7, 18, 20, 24).
   It also scrambles inline sources at column edges, though the words survive.
5. **Saturday's item boundaries are reliable** (one merge), because its items
   are marked by sign-offs and capitals openings. Its errors are almost all
   front/back matter.
6. **Text-level observations** (`text:` notes, not counted) include tilt word
   swaps, printer's marks ("VOL. I.", "3-2"), OCR of quotation marks as
   "44", and jumbled tables. They feed the completeness check and OCR
   evaluation.

The decisions these results led to, each with its evidence, are in
`v2_decisions.md`.
