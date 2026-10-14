# Article Extraction from DocLayout-YOLO Output — Plan and Status

## Goal

Turn each magazine page into **articles** (title + full text) for topic modelling
and classification, while keeping **where each article sits** (magazine, issue,
date, page, column, reading order) so juxtaposition on the page can be
studied. DocLayout-YOLO is the layout model: the evaluation
(`evaluation_error_log_documentation.md`) showed it almost never misses or
misplaces regions; its main fault is splitting articles at paragraph indents,
which is exactly what merging boxes into articles undoes.

Order of work: **penny → saturday → chambers** (chambers has 3 columns).

## Data model

The proposal (pp. 32–34) plans two linked tables: an article table (text,
topics, science/religion scores, metadata) and a region table with one row per
region–quadrant pair, joined on `article_id`. The idea is right: articles and
page positions are a many-to-many relationship, and keeping them in separate
tables joined by an id is the standard way to model it. Three changes make it
work better with YOLO output:

1. **One row per region (YOLO box), not per region–quadrant pair.** With
   YOLO a region is usually a paragraph, so repeating its text on every quadrant
   row duplicates text. Each region row stores its bounding box, column and
   reading order.
2. **Add a `pages` table** (magazine, PDF page, printed page number, issue
   number, issue date, issue start). Issue/date metadata is found once per page,
   not copied onto every article by hand.
3. **Columns instead of quadrants.** Each region's `column` is `left` /
   `right` (`left` / `middle` / `right` for Chambers' three columns, `spanning`
   for a box across columns), with its vertical position in `y_top_frac` /
   `y_bottom_frac`. Quadrants assume two columns and add little once column
   and vertical position are stored.

So the model is three tables:

| Table | One row per | Key columns |
|---|---|---|
| `pages` | page | magazine, page, printed_page, issue_seq, issue_no, issue_date, issue_start |
| `articles` | article | article_id, magazine, issue, title, title_source, start/end page, page_columns, word_count, text |
| `regions` | YOLO box | region_id, page, role, column, reading_order, bbox, text, article_id, image_file |

Topic proportions, science/religion scores, and reprint links later become
columns on `articles` (or their own tables keyed on `article_id`).

**SQLite** fits this well: a single file, built into Python (`sqlite3`), readable
straight into pandas (`pd.read_sql`), and openable in a viewer such as DB
Browser for SQLite. The pipeline writes CSVs too, so SQL is optional. Example:
what sits next to what on a page:

```sql
select r.page, r.column, a.title
from regions r join articles a on a.article_id = r.article_id
where r.magazine = 'penny' and r.page = 3 and r.role in ('title', 'text')
group by r.page, a.article_id, r.column
order by min(r.reading_order);
```

The proposal's step of having Llama 3 stitch article text across regions is
largely replaced by rules (below). An LLM is still useful later for checking
uncertain boundaries, cleaning OCR, and describing illustrations.

## Pipeline: `pipeline/yolo_output_article_extraction/`

| File | Step |
|---|---|
| `layout.py` | Load YOLO boxes; drop overlapping duplicates; assign roles and columns; find the masthead; reading order |
| `text.py` | Text for each box: Document AI OCR words assigned to YOLO boxes (or tesseract); recover text YOLO missed |
| `articles.py` | Group ordered boxes into articles; titles; cross-page stitching; figures and captions; page/issue metadata |
| `run_extraction.py` | Run it, write CSVs, SQLite, figure crops and reading-order check images |

```
python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny
python pipeline/yolo_output_article_extraction/run_extraction.py --magazine penny --pages 1-3
```

Any Python with pandas and Pillow works (e.g. the anaconda base environment).
Output: `output/article_extraction/<mag>/` (`<mag>_pages.csv`,
`<mag>_articles.csv`, `<mag>_regions.csv`, `figures/`, `reading_order/`) and
`output/article_extraction/articles.sqlite` (each run replaces that magazine's
rows).

### 1. Layout (`layout.py`)

- **Duplicates / overlaps:** boxes are taken in score order; a box at least 80%
  covered by higher-scoring boxes is dropped (YOLO's same-box/two-class
  duplicates, and low-score boxes stretched over several real ones).
- **Roles:** `title`, `text`, `figure`, `caption`, `furniture` (YOLO `abandon`:
  headers, page numbers, margins), `masthead`, `dropped`.
- **Columns:** the text area is split into equal columns (2 for penny and
  saturday, 3 for chambers). A box covering at least 20% of two columns
  **spans** them.
- **Masthead and issue starts** (`mark_masthead`, run after OCR because it
  reads the text):
  - A page starts an issue if, near its top, a short box carries masthead
    wording ("PUBLISHED EVERY SATURDAY", "PRICE ONE PENNY", "Nº 1.", "UNDER THE
    DIRECTION OF…", "Society for the Diffusion…"), or if the magazine's name is
    in large type.
  - Reading down from the top, boxes are masthead while they hold masthead
    wording, dates, or no real word ("OF THE", "1.]", OCR of the Saturday
    seal).
  - The walk stops at the first title or paragraph that belongs to an article.
  - A figure in the top 12% of the page is the masthead image. A figure lower
    down is the issue's opening illustration: it is kept, and the walk carries
    on past it.
- **Reading order:** spanning boxes (e.g. an illustration across both columns)
  cut the page into horizontal bands. Within a band: column 1 top to bottom,
  then column 2, … and the spanning box is read between bands. This handles
  articles that end and begin at an illustration's horizontal split.

### 2. Text (`text.py`)

- **OCR source:** Document AI's OCR, already produced for every sampled page,
  is far cleaner than tesseract on these stained scans (e.g. tesseract
  "sent nee" vs Document AI "relentless perseverance"). Its page coordinates
  match the YOLO rasters.
- **Words, not lines:** each Document AI word goes to the YOLO box containing
  its centre. Document AI's lines can run across both columns, so whole lines
  can't be assigned. Words keep Document AI's line grouping and word order;
  lines are split only where they cross from one box into another.
- **Words just outside a box:** words within 30 px above or below a box (YOLO
  stopping a line short) are attached to it.
- **Missed regions:** blocks of 2+ unboxed lines in a column become new text
  regions (`yolo_type = unboxed_ocr`), so text YOLO never boxed isn't lost.
  This runs before the masthead is marked, so masthead lines YOLO missed are
  also caught as masthead.
- **Joining:** hyphenated line ends are rejoined. Boxes are joined with a
  paragraph break, unless a box ends mid-sentence (a paragraph running on into
  the next column or page).
- **Fallback:** `--ocr tesseract` OCRs each box crop locally (for pages without
  Document AI output). At full scale, Document AI costs about $1.50 per 1,000
  pages beyond the free 1,000/month, so roughly $25 for all three magazines.

### 3. Articles (`articles.py`)

- A **title** box starts an article (consecutive title boxes before any text
  form one title).
- A **run-in head** starts an article: 2–6 capitalised words then a full
  stop/dash, e.g. "Animal Sagacity.—In the immense forests…". These are the
  short filler items YOLO never boxes a title for. `title_source = run_in`.
- An **attribution** at the end of a box ends its article: "…swift
  destruction.—MONTAGU'S Dedication.", "…—SOUTHEY.". The attribution must be
  Title Case or capitals, up to 6 words, and is stored in `attribution`.
  - Saturday's short untitled items end this way rather than starting with a
    run-in head.
  - A title box holding only initials ("D. C.") is also an attribution.
- **Opening in capitals:** a box whose first word is in capitals ("I HAVE sat
  upon the shore…", "HE whose heart…") starts a new untitled article. All of
  these must hold:
  - the current article already has text;
  - the previous box ended a sentence;
  - there is at least 20 px of space before the box (where the printed rule
    sits), or a column or page break. On Saturday p. 3, real item breaks have
    27–65 px of space, while a headnote running into its poem has 2–7 px.
- **Byline:** a short "FROM THE REV. WILLIAM JONES." / "BY …" / "[Abridged
  from …]" box straight after a title is stored in `byline`, not text.
- **"[To be continued.]"** ends its article and is stored in `end_note`.
- **Title notes:** bracketed parts of a title ("[Concluded from our last.]",
  "[July 15th.]") move to `title_note`.
- Other text continues the current article, **across columns and pages**: text
  at the top of a page before its first title continues the last article of the
  previous page.
- A **masthead** closes the current article: articles don't run across issues.
- **Publisher's imprint** at the end of an issue ("LONDON: JOHN WILLIAM
  PARKER, WEST STRAND", "THE COMMITTEE OF GENERAL LITERATURE…", the list of
  agents) is role `imprint`, not an article. Once found, the rest of that
  page is imprint too.
- **Figures** are linked to the article they sit in (crop saved to
  `figures/`); **captions** to the nearest figure. An untitled article opening
  with a figure takes its title from text printed in the figure ("POMPEII.",
  "HISTORY OF THE INDIAN SUPERSTITION OF JAGGANATHA"). An illustration printed
  above its article's title is moved into that article.
- YOLO mislabel fixes:
  - a "caption" over 25 words is read as text (italic headnotes);
  - an all-capitals, unbracketed "caption" is read as a title ("THE MOLE.");
  - a short all-capitals text box (2–15 words) is read as a title ("PROCESSION
    OF THE IDOL CARS TO THE TEMPLE OF JAGGANATHA");
  - a box with no letters at all is furniture ("4,060,000", stray "1 |");
  - a text box of 3 or fewer words at the foot of the page is a printer's
    signature ("VOL. I.").
- **Metadata:**
  - The printed page number comes from the header furniture (years excluded).
  - Issue number and date come from the masthead, including masthead lines
    YOLO didn't box.
  - Issue-start pages often lose the year to OCR, so the issue takes the date
    with a year from any of its pages (the last page carries it), or else the
    year of the issue before.

New article columns from these rules: `title_note`, `byline`, `attribution`,
`end_note`.

## Status

Check images in `output/article_extraction/<mag>/reading_order/` show every
page with boxes coloured by article and labelled `<reading order> · <article>`.
These are the quickest way to review results.

### Penny (26 sampled pages, 3 issues)

- **Pages 1–3 match the hand-identified articles exactly:** Reading for All;
  Charing Cross (pp. 1–2); Van Diemen's Land (pp. 2–3); Antiquity of Beer
  (crosses columns); Fair Play; Changes of Manners and Animal Sagacity (run-in
  fillers, separate rows).
- **All 26 pages:** 46 articles, 13 figures.
  - Issues on pp. 1, 9, 17 (March 31, April 7, April 14, 1832).
  - One missed YOLO region was recovered (p. 10).
- **Printed p. 24:** the capitals rule splits out the separate items "Comfort
  and good temper" and a Nelson anecdote, matching the volume index.

### Saturday (24 sampled pages, 3 issues)

- **Page 3 matches the gold standard exactly:** On the Right Use of Knowledge
  (continued); On the Study of Natural History (ends "—Journal of a
  Naturalist"); To Solitude and Answer (bylines "FROM THE REV. WILLIAM
  JONES." / "FROM G. H. GLASSE."); the untitled Montagu item; the untitled
  Southey item.
- **All 24 pages:** 35 articles, 13 figures.
  - Issues 1–3 with numbers and dates (July 7, 14, 21, 1832).
  - 8 untitled short items, each closed by an attribution or opening in
    capitals: Seneca, "A. M.", "D. C.", James Montgomery, and others.
  - 3 bylines, 1 "[To be continued.]".
  - Imprints and agents' lists excluded.

### Known issues

- **Duplicated scan pages (penny):** PDF pages 22–23 repeat printed pages
  20–21 in the sample PDF, so three articles appear twice. Fix: flag pages
  whose printed number repeats within an issue and whose text matches.
- **Spurious titles:** a verse couplet (penny p. 19) labelled `title` by YOLO
  starts an article. A run-in false positive ("Under Seven", penny p. 18) is
  likely a table.
- **Missed item breaks:** where an item neither opens in capitals after a gap
  nor ends with an attribution, it stays merged. Example: the Ghost Story
  inside The Firmament (penny p. 24). The volume index check can flag these.
- **Articles continued across issues:** penny "VAN DIEMEN'S LAND" with
  `title_note` "[Concluded from our last.]", and Saturday's Jagganátha article
  ("[To be continued.]" → issue 3). Link these with `continues_article_id`.
- **Untitled items:** the `title` column is empty for them. The attribution,
  or the index, can label them.
- **OCR errors in titles:** e.g. "SOMERS ET-HOUSE", "HISTORY OF LELLS".
- **Penny issue 2's number** isn't found (OCR'd as "2.1").

## Next steps

1. ~~Saturday~~ (done, above).
2. **Chambers (3 columns):** `COLUMNS["chambers"] = 3` is in place.
   - Check: the band/column logic with three columns; titles that span two
     columns; Chambers has no illustrations but more run-in items.
3. **Volume index as a check and title source.** Each volume opens with an
   alphabetical index of titles and page numbers (e.g. "Animal sagacity, 3";
   "Beer, antiquity of, 3"; "Charing Cross, account of, 1"). Plan:
   - OCR the index pages into an `index_entries` table (entry, pages).
   - Match each article to entries on the same printed page by word overlap.
     Entries are inverted and paraphrased, so match on content words, not
     exact strings.
   - Use the matches to:
     - validate article boundaries: an index entry with no matching article
       suggests a missed split;
     - name untitled articles;
     - correct OCR'd titles.
   - Page numbers in the index are printed page numbers, which the `pages`
     table now records.
4. **Duplicate-page detection and cross-issue continuation links** (known
   issues above).
5. **Illustrations:** store as `regions` rows (role `figure`) with a crop,
   caption and owning article. Later: a short description from a
   vision-language model.
6. **Scale-up:** run on full volumes once all three magazines look right on
   the samples. Re-check that Document AI output exists for every page, or use
   tesseract.
7. **Evaluation:** compare extracted articles with a hand list of articles for
   the 9 gold-standard pages (titles, boundaries, word counts), as was done for
   the boxes.
