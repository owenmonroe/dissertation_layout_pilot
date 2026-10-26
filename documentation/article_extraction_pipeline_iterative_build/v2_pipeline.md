# Article Extraction Pipeline — v2

The frozen v2 pipeline (git tag `extraction-v2`). It turns a scanned magazine
volume into **articles**, ready for topic modelling, classification and
juxtaposition analysis. Each article has:
- its title and text;
- front and back matter (sources, bylines, notes);
- series and continuation links;
- index terms;
- its exact place on the page.

It also records each issue's **imprint**, for publishing history.

How v2 was arrived at (the v1 evaluation, the decisions, the re-check) is in
`v1_to_v2_process.md` and the files it lists. This page describes what v2 *is*.

---

## 1. Overview

```
volume PDF ──► page images (300 DPI)
           ──► DocLayout-YOLO: layout boxes (title, text, figure, caption, abandon, table …)
           ──► Google Document AI: OCR words with positions
           ──► extraction (rule-based, this repo): boxes + words → pages, articles, regions,
                                                    imprints, index check
```

- **The models find boxes and read words. The rules decide what they are.**
  YOLO draws the layout boxes and Document AI supplies the text. Everything
  after that is rule-based and deterministic: which box is a title, where an
  article starts and ends, what is a source line, what belongs to a series.
  The rules come from printing conventions (dashes after heads, centred
  rules between items, continuation wording, position on the page), not
  from particular pages.
- **One command runs a volume:** `python pipeline/run_volume.py --volume <key>`.
- **Every number comes from the scripts.** No output is edited by hand.

## 2. Volumes

A *volume* is a run of pages from one magazine's PDF. Volumes are listed in
`pipeline/yolo_output_article_extraction/magazine_rules_config.py` (`VOLUMES`):

| Field | Meaning |
|---|---|
| `key` | names every file of the volume (`penny_1836`) |
| `magazine` | which magazine's settings and rules apply (`penny`, `saturday`, `chambers`) |
| `split` | `build`: rules were developed on it; `test`: held out |
| `pdf` | the PDF, from the repo root |
| `pages` | PDF pages holding the issues (skips HathiTrust's cover sheet and front pieces) |
| `index_pdf`, `index_pages` | where the volume's printed index is (default: the same PDF) |

| Volume | Split | Issues | PDF |
|---|---|---|---|
| `penny`, `saturday`, `chambers` | build | 1832, first three issues each (74 pages) | `build_texts/` |
| `penny_1836` | test | Nos. 270–272, June 1836 (PDF pp. 6–29; index p. 4) | `evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/` |
| `saturday_1840` | test | Nos. 482–484, January 1840 (pp. 6–29; index pp. 4–5) | `evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/` |
| `chambers_1839` | test | printed pp. 393–416, vol. 8 (pp. 7–30; index pp. 4–6) | `evaluation/evaluating_v2_article_extraction/test_texts_extraction_v2/` |

**Per-magazine settings** (`MAGAZINES` in the same file):
- column count;
- how the name is printed in the masthead;
- extra masthead wording;
- imprint wording (publisher, printer);
- whether real run-in heads are always in capitals (Chambers);
- the magazine's own editorial-notice titles (Saturday: the Committee of
  General Literature and Education).

Everything else is shared.

## 3. Running

```
python pipeline/run_volume.py --volume penny_1836              # all steps
python pipeline/run_volume.py --volume penny_1836 --steps extract
python pipeline/yolo_output_article_extraction/run_extraction.py --volume penny   # extraction only
python pipeline/yolo_output_article_extraction/check_verified.py                 # regression check
```

`run_volume.py` runs each step in its own environment:

| Step | Script | Environment | Output |
|---|---|---|---|
| page images + layout | `pipeline/run_doclayoutyolo_batch.py` | `venv_build_test/doclayoutyolo-env` | `<pdf folder>/images/<volume>_images/`, `output/output_images_json_*/<volume>_yolo/` |
| OCR | `pipeline/run_docai_batch.py` | `venv_build_test/docai-env` (Google credentials; free for 1,000 pages a month, then $1.50 per 1,000) | `output/output_images_json_*/<volume>_google/` |
| extraction | `pipeline/yolo_output_article_extraction/run_extraction.py` | any Python with pandas, Pillow, PyMuPDF | `output/article_extraction/<version>/<volume>/` |

Model output (`<volume>_yolo/`, `<volume>_google/`) goes to
`output/output_images_json_establishing_layout_AIs/` for the 1832 build
volumes (with the PrimaLayout runs from choosing the models), and to
`output/output_images_json_v2_article_extraction/` for held-out test volumes
(set by the volume's `split`). Pages already rasterized, boxed or OCR'd are skipped, so a failed run resumes
without paying twice.

## 4. Extraction, step by step

Code: `pipeline/yolo_output_article_extraction/`. For each page, in order:

### 4.1 Layout (`layout.py`)
- **Load** YOLO's boxes.
- **Drop duplicates:** a box mostly covered by a higher-scoring one is dropped.
- **Give each box a role:** title, text, figure, caption, or furniture (YOLO's
  "abandon": running heads, page numbers, margins).
- **Assign columns** from the magazine's column count.

### 4.2 Text (`text.py`)
- **Words to boxes:** each Document AI word goes to the box containing its
  centre. A word just outside a box (within 30 px above or below) joins it.
  Document AI's own line grouping and word order are kept.
- **Recovering text YOLO missed** (decision 8):
  - The scan's watermark is never text.
  - A block of unboxed lines forms a new text box only if it reads as prose.
  - A strip of single words at a box's side (page tilt) rejoins that box's
    lines.
  - A single lost line next to a paragraph box rejoins it.
  - Junk is set aside.
- **Clean-up:** printer's marks are removed ("VOL. I.", signatures), and an
  opening quotation mark read as "44" or "66" is restored.
- **Empty boxes** are dropped.

### 4.3 Printed rules (`rules.py`, decision 4)
- **Finding them:** short horizontal rules, centred in a column, are found
  in the page image. They separate items that have no title.
- **Ignored:** off-centre lines (table totals, footnote rules), lines in
  illustrations, and lines under titles or captions.
- **Effect:** a rule between two text boxes marks the lower box as a new
  item. A rule through a box splits it.

### 4.4 Masthead, reading order, page facts (`layout.py`, `articles.py`)
- **Masthead:** an issue starts on a page whose top has masthead wording or
  the magazine's name in large type. The boxes from the top until the first
  article are the masthead.
- **Reading order:** the page is cut into bands at boxes spanning columns.
  Within a band, columns are read left to right, each top to bottom.
- **Page facts:**
  - printed page number, from the running head;
  - issue date and number, from the masthead or running head;
  - an issue-number sequence check, which corrects OCR-confusable digits and
    flags new series.

### 4.5 Duplicate scan pages (`duplicates.py`, decision 9)
A page sharing 60% or more of its words with one of the six pages before it
is a duplicate scan. It is left out of the articles and recorded as
`duplicate_of`.

### 4.6 Articles (`articles.py`)
The content boxes of all pages are walked in reading order.

**What starts a new article:**
- a title box;
- a **run-in head** at the start of a paragraph ("Animal Sagacity.—In the …",
  "THE WASP. The manners …", "WHICH WAS THE GREATER FOOL?"). A head with
  lowercase words counts only with a dash after it;
- a **printed rule** above the box;
- an opening word in capitals after a finished sentence, with space or a
  column break before it;
- the **masthead**: articles never run across issues.

**What does not start one:**
- **After a colon:** a paragraph ending in a colon ("…as under:—")
  introduces what follows, so the next box continues the article.
- **Subsections:** inside an article already divided by heads, a head is a
  subsection. Chambers' mixed-case heads are always subsections.

**Front matter:** everything between the title and the first paragraph. That
includes source lines ("[From a Correspondent.]"), bylines, subtitles,
epigraphs, feast dates and continuation notes ("Concluded from No. I."). It
counts whether YOLO boxed it as a title, as text, or as the start of the
first paragraph.

**Back matter:** everything after the last paragraph.
- **A sign-off** after a dash ("…—SOUTHEY.") is cut from the paragraph and
  ends the article.
- **A source phrase without a dash** is recorded but doesn't end the article.
- **Also back matter:** short source boxes, footnotes (also ones YOLO set
  aside), bracketed editor's notes, and "To be continued" (which ends the
  part, with any source printed before it).

**Tables:** a box YOLO calls a table, or one mostly of figures with hardly any
running prose. It stays with its article but out of its text.

**Figures:**
- Captions attach to the nearest figure.
- A bracketed caption inside a figure box is recorded.
- An illustration heading the page, or carrying its own heading, belongs to
  the article below it.

**Imprint:**
- The publisher's lines at an issue's end (the magazine's imprint wording),
  including ones YOLO called a figure or furniture.
- Publisher's announcements: selling wording on the last page.
- These are not articles.

**Article type:** `editorial_notice` for notices, errata and "to
correspondents", plus each magazine's own notices. Everything else is
`article`.

### 4.7 Series and continuations (`series.py`, decision 3)

**Series** (a recurring feature):
- two stacked headings whose first recurs across issues. The leader becomes
  the series and the second heading the title ("BIOGRAPHIC SKETCHES." /
  "DR. ADAM.");
- a leader printed inside an illustration ("BRITISH ANIMALS.");
- a title recurring alone across issues, with no continuation wording ("THE
  WEEK");
- a numbered title ("… ARCHITECTURE. I.").

A leader seen in one issue only is marked a *candidate*.

**Continuations** (one piece across issues):
- A part is closed by "To be continued" and opened by "Continued.",
  "Concluded from …" or "in our first number".
- Parts are joined by title, or by series plus title, when one side has that
  wording. Otherwise they are joined by a shared distinctive title word.
- A part printed under the series heading alone takes its title from its
  continuation.

### 4.8 Volume index (`volume_index.py`, decision 4)
- The volume's printed index is parsed from the PDF's text layer: three
  columns, hanging indent.
- Each entry is matched by its distinctive words to the articles on the
  printed page it cites.
- **Output:**
  - an index check: entries matched, shared (two entries match one article,
    possibly merged items) or unmatched;
  - each article's `index_entries` (subject terms; the only heading an
    untitled filler has).
- **It never changes the articles.**

## 5. Output

**Where:** `output/article_extraction/<version>/<volume>/`:
- CSVs;
- `reading_order/` check images: each page with boxes coloured by article
  and labelled with reading order and article number;
- `figures/` crops;
- `run_info.json`.

All volumes of a version are also in `output/article_extraction/<version>/articles.sqlite`.
Every table has `pipeline_version`, `volume` and `magazine`.

**`<volume>_articles.csv`** (one row per article)

| Column | Meaning |
|---|---|
| `article_id` | `<volume>_NNNN`, in reading order |
| `issue_seq`, `issue_no`, `issue_date` | which issue |
| `title`, `title_source` | title, and where it came from (`yolo_title`, `run_in`, `figure_text`, `none`) |
| `article_type` | `article` or `editorial_notice` |
| `series`, `series_part`, `series_evidence` | recurring feature; numbered part; which rule found it |
| `continues_article_id`, `continued_by_article_id`, `continuation_evidence` | links between parts of one piece |
| `index_entries` | matching volume-index headings (" \| ") |
| `front_matter`, `back_matter` | pieces before the first / after the last paragraph (" \| ") |
| `subsections` | run-in subsection heads (low importance) |
| `start_page`, `end_page`, `pages`, `page_columns` | where it is |
| `n_regions`, `n_figures`, `word_count` | sizes |
| `text` | the article text: paragraphs, no front/back matter, no tables |
| `n_tables`, `table_text` | tables, kept out of `text` (and so out of topic modelling and WER) |

**`<volume>_regions.csv`** (one row per box)

| Column | Meaning |
|---|---|
| `region_id` | `<volume>_pNNN_rNN` (YOLO's box index; 100+ text recovered from unboxed lines; 200+ a box split at a printed rule) |
| `yolo_type`, `score` | YOLO's label and confidence |
| `role` | `title`, `series_heading`, `text`, `table`, `figure`, `caption`, `front_matter`, `back_matter`, `masthead`, `imprint`, `furniture`, `dropped`, `duplicate_page` |
| `column`, `band`, `reading_order` | place in the page's reading order |
| `article_id` | its article |
| `x1 … y2`, `y_top_frac`, `y_bottom_frac` | position (pixels; share of page height) |
| `text`, `caption` | OCR text; a figure's caption |
| `front_text`, `back_text` | front/back matter cut from this box's text |
| `image_file` | figure crop |
| `note` | why a rule changed this box |

**`<volume>_pages.csv`:**
- printed page, issue date and number, issue start;
- masthead text;
- box counts;
- unboxed OCR text;
- `duplicate_of`;
- `issue_seq` and `issue_check`.

**`<volume>_imprints.csv`:** one row per issue. Its number, date, page and
the full imprint text (publisher, printer, agents, price), for publishing
history across volumes.

**`<volume>_index_check.csv`:** one row per index entry citing a page in the
run. The entry, the page, the matched article, and the status.

**`run_info.json`:** the version, git commit, whether the code had
uncommitted changes, run date, volume, magazine, split, PDF, pages, and OCR
used.

## 6. Versions and freezing

- **Code:** `PIPELINE_VERSION` in `run_extraction.py` decides the output
  folder. A version in `FROZEN_VERSIONS` refuses to write.
- **Tags:** v1 = `extraction-v1` (evaluated on the development pages);
  v2 = `extraction-v2` (this page).
- **Test output from frozen code:** the test volumes were run with v2 on
  2026-10-16. Their `run_info.json` records commit 2472eb78 with no
  uncommitted changes; that commit differs from the tag only in
  documentation (the pipeline code was checked identical first). v2 was then
  added to `FROZEN_VERSIONS`, and new work goes into v3.
- **Regression check:** `check_verified.py` re-extracts the hand-verified
  pages in `verified_pages.json` and compares articles and reading order.
- **Re-check against a log:** `evaluation/evaluating_v1_article_extraction/compare_versions.py` (or the
  `.ipynb`) looks up every box of an annotated log in another version's
  output.

## 7. Known limits

- **No italics:** OCR without style information. A few heads and sources
  are known only by italics.
- **Missed items:** a filler with no title, no head and no printed rule is
  merged into the item before it. The index check flags these.
- **Unmarked front matter:** front matter written as ordinary prose, with
  no marker (an editor's introduction, an epigraph run into the first
  paragraph), stays in the text.
- **Heavy page tilt** can still scramble a head or a footnote.
- **Series heading on one page only:** a piece printed under another
  piece's series heading, with no heading of its own (the Swallow), isn't
  put in the series.
- **Untitled editorial pieces:** editorial pieces without notice-style
  titles stay `article`.
- **Tables and subsections** are labelled but not structured (low importance
  for the study).
