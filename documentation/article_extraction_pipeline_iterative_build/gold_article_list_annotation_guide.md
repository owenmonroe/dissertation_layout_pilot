# Gold Article List — How to Annotate the Test Volumes

The baseline evaluation of the frozen pipeline (roadmap step 5). For each
held-out test volume, list every article exactly as printed in
`evaluation/evaluating_v2_article_extraction/gold_article_list_test.csv`. Later, a scoring script will match
any pipeline version's articles to this list and compute:
- article boundaries (precision and recall);
- titles;
- front and back matter found;
- series and continuations;
- imprints.

The list doesn't depend on any pipeline output, so it scores v2 now and any
later version without annotating again.

## The one rule: annotate from the pages, not the output

Work only from the printed pages:
- the PDFs in `evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/` (issue pages below), or
- their plain page images, `evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/images/<volume>_images/`.

**Don't open** anything in `output/article_extraction/` for these volumes
(the CSVs, or the `reading_order/` check images) until the list is finished.
Seeing the pipeline's choices would bias the gold.

| Volume | PDF | Issue pages (PDF) | Issues |
|---|---|---|---|
| `penny_1836` | `penny_test_3issues_v5_1836_…pdf` | 6–29 | Nos. 270, 271, 272 (Monthly Supplement), June 1836 |
| `saturday_1840` | `saturday_test_3issues_v18.19_1841_…pdf` | 6–29 | Nos. 482–484, January 1840 |
| `chambers_1839` | `chambers_test_3issues_v8_1839_…pdf` | 7–30 | three issues, printed pp. 393–416 |

The cover sheet, front pieces and index pages aren't annotated. Page numbers
in the list are **PDF page numbers**: the page as the PDF viewer counts it,
including the cover sheet.

## Columns

One row per item, in reading order.

| Column | What to write | Example (1832 build pages) |
|---|---|---|
| `gold_id` | running number within the volume: 1, 2, 3 … | `12` |
| `volume` | the volume key | `penny_1836` |
| `issue_no` | the issue's number as printed | `271` |
| `issue_date` | as printed, with the year | `June 25, 1836` |
| `start_pdf_page` | PDF page where the item begins | `15` |
| `start_printed_page` | its printed page number (blank if none is printed) | `242` |
| `start_column` | where it begins: `left`, `middle`, `right`, `spanning` | `right` |
| `end_pdf_page` | PDF page where it ends | `16` |
| `article_type` | `article`, `editorial_notice` (notices, errata, "to correspondents"), `imprint` (the issue's publisher/printer lines; one row per issue), `announcement` (publisher's adverts) | `article` |
| `title` | the title as printed, without its full stop; for a run-in head, the head ("Animal Sagacity"); blank if untitled | `THE ZOOLOGICAL GARDENS` |
| `first_words` | the first 6–8 words of the **body text**, after the title and any front matter | `THE greater number of our readers must` |
| `last_words` | the last 6–8 words of the body text, before any back matter | `and the more entitled to be called useful` |
| `front_matter` | everything between the title and the body: source lines, bylines, subtitles, epigraphs, dates, continuation notes. Several pieces: separate with ` \| ` | `[From Crabbe's Parish Register.]` |
| `back_matter` | everything after the body: sign-offs and sources, footnotes, editor's notes, "To be continued". Several pieces: ` \| ` | `Library of Entertaining Knowledge` |
| `series` | the recurring feature it belongs to, if any | `British Animals` |
| `continued_from` | `yes` if it continues a piece from an earlier issue (add the earlier title in `notes` if known) | `yes` |
| `to_be_continued` | `yes` if it says it continues in a later issue | `yes` |
| `notes` | anything uncertain or unusual | `head scrambled by tilt` |

Copy words as printed. OCR differences don't matter: the scoring script
matches words loosely. If a field doesn't apply, leave it blank.

## Conventions

These are the same as the v1 evaluation (`v1_evaluation.md`).

- **What counts as an item:**
  - every titled article;
  - every run-in-head piece ("THE WASP.—…");
  - every untitled filler (a paragraph set off by a printed rule, or ending
    with its own source);
  - editorial notices, each issue's imprint, publisher's adverts.
- **One row per item,** even when it runs across columns or pages.
- **What doesn't get its own row:**
  - a quoted poem or passage inside an article;
  - a subsection;
  - a table;
  - a caption.
  These are part of their article.
- **Series pieces:** each piece under a recurring heading is its own row,
  with the series name ("BIOGRAPHIC SKETCHES." / "DR. ADAM." → series
  `Biographic Sketches`, title `DR. ADAM`). The series heading is not the
  title.
- **Continuations are not series.** Each part is its own row; mark
  `continued_from` / `to_be_continued`.
- **Front and back matter go by position,** not kind. Before the body is
  front matter; after it is back matter, including footnotes and
  "[To be continued.]".
- **Leave out:** the masthead, running heads, page numbers and printer's
  signature marks.
- **Uncertain cases:** decide, and say so in `notes` with `uncertain:`.

## Scoring (built 2026-10-22)

The list is complete: 96 rows (corrected 2026-11-02), annotated without seeing the output. It is
scored by `evaluation/evaluating_v2_article_extraction/score_gold.py`, run from `evaluation/evaluating_v2_article_extraction/evaluate_v2_with_gold.ipynb`.
Set `VERSION` in the notebook to score another version against the same list.

- **Matching:** each gold item is located in the output by its first and last
  words. Matching tolerates OCR noise and is limited to the item's own pages.
- **Item outcomes:** exact / merged / split / lost.
- **Boundaries:** recall and precision.
- **Fields:** title, front/back matter pieces (footnotes separately), series,
  continuations, editorial notice, illustration count, issue number and date.
- **Imprints.**

Outputs in `evaluation/evaluating_v2_article_extraction/`:
- `gold_eval_<version>_items.csv`, `_pipeline_articles.csv`, `_pieces.csv`,
  `_imprints.csv`;
- `gold_eval_<version>_summary.md`.

Every number comes from the script.

**Mapping:** the gold list calls the Chambers volume `chambers_1840` (its
issues are dated 1840); the pipeline's key is `chambers_1839`. The scorer
maps one to the other.

**Convention difference:** v2 treats a numbered title ("On Garden Herbs. I.")
as a series part, but the gold list doesn't. These show as "extra series" in
the results.
