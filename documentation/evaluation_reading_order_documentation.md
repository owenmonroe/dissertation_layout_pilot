# Evaluation — Reading Order and Article Assignment

## Purpose

Hand-evaluation of the article-extraction pipeline
(`pipeline/yolo_output_article_extraction/`, see `article_extraction_plan.md`):
for every box it placed, is the box in the right reading order, the right
article and the right role? This is the second evaluation after the box study
(`evaluation_error_log_documentation.md`), with matching error types where
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
| `verdict` | pre-filled `ok`; set to `error` for a wrong box |
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

### Conventions

- Only errors are changed; every other row stays `ok`.
- Several errors on one box go in one row, joined with `; `, in a fixed order
  (as in the box study).
- An article boundary error is logged once, where the boundary should be (or
  wrongly is), not on every box of the article.

## Workflow

Page by page, with Claude Code. For each page, Claude lists the boxes in
reading order (number, column, role, article, first words). Owen compares
them with the check image and replies `ok` or names the errors by reading-order
number. Claude records them in the log. Order: penny → Saturday → Chambers,
page 1 onward.

## Progress

Not started (template built 2026-10-14: 1,086 boxes — penny 334, Saturday
336, Chambers 416).
