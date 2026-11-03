# Article Extraction — v3 Decisions

Changes for v3, drawn from scoring frozen v2 against the gold article list of
the test volumes:
- **results:** `evaluation/evaluating_v2_article_extraction/v2_gold_comp_eval_*`;
- **gold list:** `gold_article_list_test.csv`;
- **guide:** `gold_article_list_annotation_guide.md`.

Each entry gives the decision, the evidence (volume, gold item or PDF page),
and its status, in the same format as `v2_decisions.md`.

**Status key:** `proposed` (from the evidence, not yet agreed) → `decided` →
`built` → `checked` (re-scored). Rules follow printing conventions and must
generalise (Owen, 2026-10-16); a miss that only one page shows stays a known
miss.

**v2 baseline, as first scored** (85 gold items; corrected figures are in the table below):
- 72% exact; boundary recall 93%; boundary precision 64% (44 extra pipeline
  articles);
- titles 81%; back matter in place 58%; front matter in place 13%;
- Chambers issue numbers and dates 0%.

**Owen's priorities for v3 (2026-10-26):**
1. The Chambers masthead must not produce or split articles (decision 2).
2. Poetry without a title must not be lost (decision 3).
3. Better front- and back-matter detection (decisions 5, 6, 7).
4. Issue numbers read from each issue's first-page masthead, whose format
   differs by magazine and even by issue (decision 2).
5. **Splitting in Chambers and Saturday** (decisions 1, 10, 11, 5).

**Where v2's 44 false splits come from** (each extra article classified by
its first box):

| Cause | Chambers | Saturday | Penny | Total | Decision |
|---|---|---|---|---|---|
| Printed rule, mid-sentence (the footnote-rule bug) | 14 | 1 | 0 | 15 | 1 |
| Masthead lines | 8 | 0 | 0 | 8 | 2 |
| Headings inside an article (a quoted play's "SCENE", "Flaw-Finder.", "(Charge to the Jury.)", "L.466,089", a quoted inscription) | 5 | 0 | 0 | 5 | 10 |
| Printed rule at a sentence start (section breaks within an article) | 2 | 2 | 0 | 4 | known limit |
| Front matter splitting title from text (the Calendar's table, the Months poem, Quack Advertisements' quoted note) | 2 | 2 | 0 | 4 | 5 |
| A figure box opening an article | 0 | 3 | 0 | 3 | 11 |
| Other (a footnote as title, OCR junk, a capitals opening, a title and its "No. I." split) | 0 | 3 | 2 | 5 | 7, 9 |
| **Total** | **31** | **11** | **2** | **44** | |

**Open questions:** none (8a and 8b decided 2026-10-26).

## v3 results so far (2026-11-02)

All decisions below are built. v3 is **not frozen yet**. Scores are on the v2
test volumes, which are now build texts, so they show the fixes worked, not
how v3 does on unseen text. That comes from the new held-out issues.

| Against the corrected gold list (87 items) | v2 | v3 |
|---|---|---|
| Exact items | 63 (72%) | 82 (94%) |
| Merged | 4 | 2 |
| Split | 16 | 2 |
| Lost | 4 | 1 |
| Boundary recall | 93% | 98% |
| Boundary precision | 66% | 97% |
| Extra pipeline articles | 42 | 3 |
| Pipeline articles | 123 | 88 |
| Titles | 81% | 99% |
| Front matter in place | 20% (3/15) | 87% (13/15) |
| Back matter in place | 64% | 83% |
| Footnotes in place | 25/36 | 30/36 |
| Series (where either has one) | 28% (7/25) | 67% (10/15) |
| Issue number | 26% | 100% |
| Issue date | 51% | 100% |

Numbers from `evaluation/evaluating_v2_article_extraction/v3_gold_comp_eval_*`.

- **1832 pages:** the 5 verified pages pass. Of the 971 rows logged ok, 957
  are unchanged, 13 renamed, and 1 changed (the intended Saturday p12 fix).
  Logged-error outcomes are unchanged from v2
  (`evaluation/evaluating_v1_article_extraction/reading_order_v1_vs_v3.csv`).
- **Gold list corrected by Owen (2026-11-02):** issue 416's date; two rows
  added ("The brave only know…", Sterne; "Do not suffer your mind…", Mrs.
  Child); Tillotson put on the row that had Sterne. Now 96 rows. **Gold IDs
  after those rows moved up by 1–2, so gold numbers in the decisions below
  use the earlier numbering** (Saturday 26–49 +1, 50 +2; Chambers
  +2).
- **Gold list corrected again by Owen (2026-11-02):** front-matter slips
  (last words entered as front matter) corrected and the Coal Miners'
  "[From a Correspondent.]" added. 96 rows, 15 front-matter pieces.
- **Locke and Helvetius were found.** OCR reads "LOCKR." and "HELVvetius.";
  the pipeline cut both into back matter. The scorer now tolerates a letter or
  two of OCR noise in one-word sources.

---

## 0. Test texts and versions for v3

**Decision.** The v2 test volumes (`penny_1836`, `saturday_1840`,
`chambers_1839`) have now been seen, and v3's rules are written from them, so
for v3 they become build texts.
- **Keep scoring them,** as development numbers: v3 against the same gold
  list (`evaluate_v2_with_gold.ipynb`, `VERSION = "v3"`) shows what each fix
  gained.
- **Keep checking the 1832 pages:** `compare_versions` against the v1 log
  catches regressions there.
- **v3's honest numbers** come from a **new** set of held-out issues with
  their indexes, annotated the same way before the output is seen.

**Status:** decided (2026-10-26). Owen has added the new held-out test texts
and their gold list in `evaluation/evaluating_v3_article_extraction/`. They
stay unopened until v3 is frozen.

## 1. Printed rules must not start an item mid-sentence

**Decision.** Two changes to the printed-rule rule (decision 4 of v2):
- **(a) Fix a bug.** When a footnote under its rule is taken as back matter,
  clear the rule mark on the box above it. Otherwise the next box in reading
  order (often the next column or page, continuing the same sentence) is
  taken as a new item. v2 clears it only for footnotes whose asterisk OCR
  garbled.
- **(b) A general safeguard.** A printed rule never starts a new item when
  the box above ends mid-sentence, or the box below starts in lowercase. A
  new item starts a new sentence.
- **(c) A final check, whatever the cause.** After the articles are built,
  an untitled article whose text starts mid-sentence is joined back onto the
  article before it. Mid-sentence means a lowercase first word, or the
  previous article ends on a hyphen or without finishing its sentence. This
  catches splits from any cause (rules, page turns, figures, OCR), not only
  the footnote rule.

**Evidence.**
- 19 of the 44 extra articles were started by a printed rule; 16 of those
  start mid-sentence, 13 of them in Chambers ("are bound together…",
  "dustrious habits…", "grapher of Johnson…").
- Example: `chambers_1839` PDF p7 → p8 (check images
  `chambers_1839_page_007_order.jpg` / `_008_order.jpg`).
  - Living in Paris ends p7's right column with "…by which young men", above
    a footnote rule and "* The French pound is…".
  - p8 continues "are bound together in London…", but as article 4.

**Status:** built and checked 2026-11-02. The rule above a footnote no longer marks a new item; a rule needs the box above to finish its sentence; `rejoin_fragments` is the final check. Refined by the 1832 check: a box under a real rule stays a new item even if OCR makes it start in lowercase (Chambers 1832 p16), and an article closed by a sign-off or "To be continued" takes no fragment (p20).

## 2. Mastheads and issue numbers (all three magazines)

**Decision.**
- **Issue-number formats per magazine, in the config.** The number is
  printed differently by magazine and even by issue: "No. 270", "Nº 482",
  "NUMBER 414", "272.]". Each magazine lists its formats in
  `magazine_rules_config.py`, and "NUMBER 414" counts like "No. 414", both
  for reading the number and for recognising the masthead.
- **Sequence check:** fill from neighbours. When consecutive issues are
  confirmed by continuous printed page numbers, an issue whose number can't
  be read, or reads out of sequence, gets its neighbour's number ±1, marked
  as inferred in `issue_check`. A Penny issue read as "10" between 270 and 272
  becomes 271 (inferred).
- **The masthead band:** on an issue's first page, the row of short boxes
  across the top above the first title (number, date, price, printer, the
  editors' line) is all masthead, read across the columns, not column by
  column.
- **Chambers config:** add "editors of" to Chambers' masthead wording.
- **Issue date:** read from the masthead band's date line.

**Evidence.**
- `chambers_1839` PDF pp. 7, 15, 23: "NUMBER 414.", "SATURDAY, JANUARY 4,
  1840.", "PRICE THREE HALFPENCE.", "PRINTED BY BRADBURY AND EVANS…" and "BY
  WILLIAM AND ROBERT CHAMBERS, EDITORS OF…" became titles, series headings
  and articles.
- These account for about 10 extra articles and 3 wrong titles, and split
  each issue's first article (Living in Paris into four).
- Chambers issue number and date: 0% (39 items). Penny 271 read as "10";
  Penny 270 and Saturday 484 not read.

**Status:** built and checked 2026-11-02. Issue number and date 100% on the test volumes (were 26% and 51%). All three magazines' formats are in the config, including Saturday's `№` and Penny's `270.]` read as `270.3`. Dates now come only from the masthead and running head, with ordinals ("18TH") and ranges ("May 31 to June 30, 1836"). A tall illustration near the top is no longer masthead. Saturday 484 is `inferred` from its neighbours.

## 3. Content that YOLO calls page furniture

**Decision.** A YOLO `abandon` box inside the text area (not the running head
or page-number band, not a margin) with 12 or more words is content, read as
text. Short `abandon` boxes stay furniture.

**Evidence.**
- Three untitled Saturday poems lost:
  - gold 22 ("Blest Solitude!…"), 44 ("Oh, Charity!…") and 47 ("No radiant
    pearl…");
  - YOLO `abandon` with confidence 0.66–0.86, at 74–84% down the page.
- Known miss: "END OF THE EIGHTH VOLUME." (Chambers gold 93), which has 5
  words.

**Status:** built and checked 2026-11-02 (`promote_content` in `text.py`). The three poems are recovered. A box is promoted only in body-size type (0.85 of the body's line height or more): the poems measured 0.88–0.96, lost-mark footnotes 0.74. A recovered box starts its own item. Known miss as stated ("END OF THE EIGHTH VOLUME."; also Chambers gold 92, a notice in small type).

## 4. Captions taken as titles

**Decision.** An all-capitals YOLO caption becomes a title only when no title
box follows before the text. Otherwise it stays the illustration's caption.
The v1 rule was made for "THE MOLE.", which has no title of its own.

**Evidence.**
- "FLOATING TIMBER IN LOMBARDY" for The Timber-Floats of Germany and Italy
  (Saturday gold 30).
- "RUINS OF THE ABBEY OF ST. BERTIN…" for St. Omer's, in France (gold 42).

**Status:** built and checked 2026-11-02 (`caption_opens_article`). Wider than proposed: a capitals caption mid-article ("GOTHA.", "RICHMOND CASTLE") is also a caption, when the next text starts mid-sentence. Under a *recurring* leader the caption is the title ("BRITISH ANIMALS." / "THE DORMOUSE.", caught by the 1832 check).

## 5. Front matter between title and text

**Decision.** What sits between a title and the first prose paragraph is
front matter, and **front matter never starts a new article**:
- **Generic headings:** a heading that only says "Introduction", "(First /
  Second / …) Article", "Continued" or "Concluded" is front matter (a
  continuation note where it says so), not the title.
- **Verse or a quotation under the title** (an epigraph) is front matter:
  short lines narrower than the column, or smaller type than the body (from
  the OCR line heights), or a quotation ending with its author's name.
- **"By …" lines and subtitles** ("A Spanish Tale, By W. …", "Story from the
  Causes Celebres") are front matter. v2 already does this when YOLO boxes
  them separately; v3 also does it when they open the first paragraph box.
- **The article continues afterwards:** the first full prose paragraph after
  the front matter stays in the same article, never a new one.

**Evidence.**
- Front matter splitting title from text: the Calendar (Saturday gold 21,
  front-matter table); the Natural History of the Months (gold 27, Spenser
  epigraph); Quack Advertisements (Chambers gold 57, quoted note).
- Front matter left in the text or lost: Saturday gold 27, 33 (Nineveh
  epigraph), 48; Chambers 56, 65, 70; Penny 5, 15 (bracketed sources opening
  the text).
- "INTRODUCTION" for On Garden Herbs. I. (Saturday gold 48).
- "SECOND ARTICLE" for Speculation on Words (Chambers gold 87; also front
  matter of M. Turgot, gold 80).

**Series after the run-in rule (Owen, 2026-11-02):** all 6 gold series are now found (10/15 items). A run-in opening printed in two issues over different subjects is a series ("National Galleries… at Munich. The Glyptothek"). "A Discourse on Geology" is a series, added to the gold list: a main title over a number and a subject expected to change, so the number is `series_part`, not a continuation part. It stays a candidate until it recurs. The 5 misses are later items under one leader (Remarkable Cases, Last Century Anecdotes), left for now because the end of such a group can't be found reliably.

**One category (Owen, 2026-11-02):** headers, subtitles, bylines and source lines are all `front_matter`, with no separate fields. They read on the page as a byline or header, and they matter because they indicate an article's source.

**Status:** built and checked 2026-11-02 (`is_epigraph`, `GENERIC_HEADING`). Front matter in place 20% → 87%. Owen (2026-11-02): headers, subtitles, epigraphs and bylines that a reader sees set apart from the text matter most, even when YOLO boxed them into a paragraph. "London, May —, 1835.—" (Chambers gold 78) and the Calendar (Saturday gold 21) are the accepted misses. The signal used: the next box opens in capitals, as a first paragraph does, or the box signs itself off as a quotation and runs on. A heading after a byline is a subtitle. Three later rules, all from Owen's reading of the page: a short line centred under the title is front matter (`centred_under_title`: "(From Sharon Turner's…", "Second Article."); an all-capitals line with no YOLO box is a heading, and one centred at the top of a paragraph box is split off (`recover_unboxed`, `split_headings`, tables excepted); such a split line under a title ending in a full stop is a subtitle, and under a title with no stop it continues the title. This also recovered "THE HEIR OF THE ST GERANS.", which was lost, and the whole of "English Ingenuity and Enterprise in a New Point of View". Boxed headings don't take the full-stop test because series leaders end in stops too.

## 6. Sign-offs

**Decision.** Sign-offs not caught by v2's rules:
- **With a dash:** keep the 2–12 word check and starting with a capital, but
  drop the title-case check. The dash is the signal ("—Newspaper paragraph.",
  "—Ayr paper.").
- **On its own last printed line:** a short phrase starting with a capital
  (1–8 words) that stands alone on the box's last line is a sign-off, with
  or without a dash ("Sterne.", "Locke.", "Crabbe."). This uses the OCR's
  line positions.

**Evidence** (back matter left in the text or missing):
- Saturday gold 25 "Sterne.", 26 "Locke.", 36 "Brown", 38 "Crabbe.", 46
  "Helvetius.";
- Chambers gold 62 "The Hand-Book to Paris.", 72 and 75 "Newspaper
  paragraph.", 73 "Dr Channing's Pamphlet on Self-Culture.", 74 "Hood's Comic
  Annual, 1830.", 77 "Waverly Novels, new edition.", 90 "Travels in North
  America, by the Hon. C. A. Murray. 1839.", 91 "Ayr paper.";
- Penny gold 2 "Dr F. Lieber, Plan of Education…".

**Status:** built and checked 2026-11-02 (`attribution`, `last_line_source`). Back matter in place 64% → 83%. A dash phrase may have up to two lowercase words, not in verse, and not with a word broken across lines. A last-line source must be set to the right.

## 7. Footnotes (Chambers especially)

**Owen's concern (2026-10-22).** Chambers prints footnotes under the columns,
below a short rule and in smaller type. They should be back matter of the
article they annotate, but the rule and their position can make them look
like new items or page furniture. Example: `chambers_1839` PDF p7.
- Lower left: "* The *entresol* is little known in London…" and "† Although
  the taxes on houses…" in one YOLO `abandon` box under the left column.
- Lower right: "* The French pound is equal to…" under the right column.

**What v2 does with them (checked on the test volumes):**
- **Recognised:** a footnote whose OCR kept its mark (`*`, `†`) is
  recognised and made back matter, whether YOLO called it `abandon` or text.
  Both corners of p7 were handled this way.
- **Wrong article:** most "missing" footnotes went to the **wrong article**.
  v2 attaches a set-aside footnote to "the article on the page whose text has
  the asterisk, otherwise the page's last article". On a three-column page
  with several articles, more than one has an asterisk, and it takes the
  last. 6 of the 7 missing Chambers footnotes are this (gold 52, 54, 65, 67,
  84, 86): e.g. Hibernation's "* Irritability is a term…" (p9) went to the
  article after it.
- **Lost mark:** a footnote whose mark OCR lost is left as furniture (gold
  87, "Nish is the word…", p28).
- **Splits:** the rule above a footnote can split the article it sits under
  (decision 1).

**Decision.** General rules, by position and type size rather than
particular pages:
- **(a) Attach by mark first, then position.** Owen (2026-10-22): a column
  can hold two or more articles above its footnote, and the note may belong
  to the top one, the one with the asterisk. So:
  1. Search **up the footnote's column** for the nearest article whose text
     has the **same mark** (`*`, `†`, `‡`). That article gets it.
  2. If no article in the column shows the mark, search the rest of the page
     the same way (a footnote under one column can annotate another).
  3. Only if OCR lost the mark everywhere, fall back to the article directly
     above the footnote in its column. v2's "the page's last article" is
     dropped.

  Some misses are acceptable (Owen), e.g. where OCR drops the mark in the
  text and two articles share the column.
- **(b) Recognise by type and place, not only by the mark.** A box at the
  foot of a column, below a printed rule, set in smaller type than the page's
  body text, is a footnote, even when OCR lost the mark. Type size comes
  from the OCR line heights.
- **(c)** The rule above a footnote never starts a new item (decision 1).
- **(d)** A YOLO *title* box starting with a footnote mark ("* Belzoni") is a
  footnote too, not a title (Penny gold 5).

These should be low-risk. The signals (foot of the column, a rule above,
small type) are how footnotes are printed in all three magazines.

**Evidence.** Chambers gold 52, 54, 65, 67, 84, 86 (wrong article), 87 (lost
mark); p7 (both corners handled, but see decision 1). Also 5 footnotes left
in the text in Penny and Saturday (Penny gold 5, 17; Saturday 31, 33):
check whether (b) catches them.

**Status:** built and checked 2026-11-02 (`footnote_owner`, `lost_mark_footnote`). Footnotes in place 25/36 → 30/36. Remaining: 3 footnotes left in the text and 3 attached to another article.

## 8. Series over several pieces; numbered titles

**Decision.**
- **(a) One heading over several pieces: the volume index as evidence.**
  Owen (2026-10-26): the indexes do group pieces under headings, but not
  always as our series. Some groups match a printed series heading (Penny:
  *Old English Ballads* and *Romantic Ballads*, each over several poems,
  which Owen reads as two series). Others are the compiler's own categories,
  printed nowhere (*Poetry*). So:
  - **Parsing:** the index parser splits a heading and its sub-entries into
    (group → sub-entry → page) triples. v2 runs them together as one entry.
  - **`series`** stays defined by what is printed. An index group becomes a
    piece's series only when the group's name is also printed as a heading
    in that issue. The index then extends the printed heading to the pieces
    under it that carry no heading of their own (the Swallow, the five
    *Remarkable Cases of Circumstantial Evidence*).
  - **`index_group`** (new article column) records the index's grouping for
    every matched piece, printed or not (*Poetry*). It is subject metadata
    for classification and topic work, never a series by itself.
  - No page-layout rule for this (see v2 decision 3: "the next piece on the
    page inherits the series" would misfire).
- **(b) Numbered titles: series or continuation?** Owen (2026-10-26):
  - **Continuation:** one piece carried on in parts. The title stays the
    same apart from a part number ("I.", "II.", "No. 3") or a note
    ("Continued", "Second Article"). "On Garden Herbs. I." and "II." are one
    piece in parts, not a series.
  - **Series:** a recurring heading (the leader) over pieces with
    **different** subject titles, which often don't continue each other.
    "Biographical Sketches: Washington", then "Biographical Sketches:
    Napoleon".
  - **Both:** inside a series, a subject carried on is a continuation within
    it. "Biographical Sketches: Napoleon" and "Biographical Sketches:
    Napoleon (continued)" are in series *Biographical Sketches*, and the
    second continues the first. This is the same as Archery inside Column
    for the Boys in v2, and Owen expects the pattern often.

  **In the pipeline:**
  - **Numbered titles:** a numbered title no longer makes a series (v2's
    rule is dropped). The number becomes the piece's **part** (new column
    `part`), and parts with the same base title are linked as one
    continuation (`continues_article_id`). Part 2 or later counts as
    continued from an earlier part.
  - **Series numbers:** a number on the series heading itself
    ("Biographical Sketches. No. III.") stays the series' own numbering
    (`series_part`).
  - **Series** still need a leader recurring over different subject titles
    (v2 decision 3); subjects repeated under the same leader are
    continuations within it.

  **Follow-ups agreed (Owen, 2026-10-26):**
  1. **Part I implies "to be continued"**, even if nothing is printed. A
     later part ("No. III", "Second Article") is continued from an earlier
     part. It is to be continued only if the page says so.
  2. **A title recurring alone is a series** ("The Week"): its name and
     format recur, not its content. Its pieces may or may not carry their
     own subheading (the week's dates, a month's name).
  3. **A number on the series heading is the series' numbering:** "The
     Natural History of the Months. I. January" is series *The Natural
     History of the Months*, series number I, title "January". "I. January"
     as the full title is also acceptable.
  4. **Inferred continuation** from "I.", "Part II", "Second Article" is
     recorded without proof of the other parts, and without a link when the
     earlier part wasn't processed (`continues_article_id` empty). This is an
     inference from the printed wording, which Owen accepts; links come once
     whole volumes are run.

**Evidence.**
- "Remarkable Cases of Circumstantial Evidence" over 5 Chambers pieces (gold
  81–85; only the first gets it).
- "National Galleries for the Fine Arts at Munich" (Penny gold 4, 13).
- "Last Century Anecdotes" (Chambers gold 67–68).
- Numbered titles flagged "extra series": Saturday gold 31, 42, 43, 48;
  Penny 14; Chambers 87. Under (b) these are continuations, which agrees
  with the gold list.
- Series with continuation in the gold list: M. Turgot (Chambers gold 69, 80:
  series Biographical Sketches, continued).

**Status:**
- **(b) built and checked 2026-11-02.** New columns `part`, `continued_from`,
  `to_be_continued`. "Extra series" from numbered titles are gone; continued
  from 99%, to be continued 98%.
- **(a) partly built.** An index entry headed by a printed series heading
  extends that series to the pieces it names (`extend_series`): the Swallow is
  in British Animals with no hand correction, and `index_group` records the
  group.
- **Not built:** the compiler's own categories (*Poetry*). On the later
  volumes the index's OCR text layer is too scrambled to parse groups
  reliably, and Chambers' index is arranged differently. Re-running OCR on
  the index pages would be the route.
- **Known miss:** "Remarkable Cases…" (4 pieces), "National Galleries…" (2),
  "Last Century Anecdotes" (1): the indexes didn't yield them.

## 9. Smaller items (known limits unless cheap)

- **Printed rules at a sentence start inside an article** (section breaks:
  Saturday On Garden Herbs, Chambers 2 cases). Indistinguishable from a
  rule between items without reading the content. Known limit; the index
  check may flag them.
- **A title split from its own "No. I."** (Penny gold 17, "THE TOWER OF
  LONDON.—No. I." boxed as text after the title). Check after decision 5.
- **Front matter written as prose or verse** (epigraphs, editor's
  introductions: Saturday gold 27, 33, 48; Chambers 57) stays in the text.
  Known limit without italics.

**Status:** noted.

## 10. Headings inside an article

**Decision.** A YOLO title box doesn't start a new article when it is part
of quoted or tabular matter inside one. That is, when it:
- follows a paragraph ending with a colon (introducing what follows, as v2
  already does for run-in heads);
- is in quotation marks or parentheses ("(Charge to the Jury.)",
  ""Flat Stones are Better and Cheaper—"");
- is mostly figures or a sum ("L.466,089").

It stays in the article as text (or a subsection). Character and scene
headings in a quoted play ("SCENE.—An Inn.", "Flaw-Finder.") follow the
same rule when introduced by a colon.

**Evidence.** Chambers gold 53 (Fugitive Writings of James Boswell, a quoted
play split into four articles), 54 ("L.466,089"), 71 (Grave Literature,
quoted inscription).

**Status:** built and checked 2026-11-02 (`inside_article`). "L.466,089", "(Charge to the Jury.)" and the quoted inscription now stay in their articles. Boswell's quoted play is still split at "Flaw-Finder.", because a verse line reads as a sign-off just before it.

## 11. Figure boxes don't open articles

**Decision.** An illustration never opens an article by itself:
- **Where it goes:** it goes to the titled article that follows it on the
  page (v2's "heads the page" rule), or else to the article being read.
- **Running heads:** running-head text caught inside a figure box ("THE
  SATURDAY MAGAZINE. 1840.]") is removed from the figure's text.

**Evidence.** Saturday: 3 extra articles opened by figure boxes (running head
inside the box, or OCR junk from the engraving).

**Status:** built and checked 2026-11-02 (`move_lone_figures`, `figure_title`). Also: a heading in a figure box can give the title ("ST. OMER'S, IN FRANCE. I.", "THE GIRAFFES AT THE ZOOLOGICAL GARDENS").

---

## Build order and checks

**Order: biggest gain and lowest risk first.**

| Step | Decisions | Expected effect (v2 test volumes) |
|---|---|---|
| 1 | 1 (rules mid-sentence, final continuation check) + 7 (footnotes) | about 16 fewer extra articles; Chambers footnotes on the right article |
| 2 | 2 (mastheads, issue numbers) | about 8 fewer extra articles; Chambers issue numbers and dates read; Penny/Saturday numbers filled |
| 3 | 3 (`abandon` content) | 3 lost poems recovered |
| 4 | 10, 11 (headings inside articles, figures) | about 8 fewer extra articles |
| 5 | 4, 5 (captions, front matter) | about 4 fewer splits; titles and front matter better |
| 6 | 6 (sign-offs) | up to 14 sources moved from the text to back matter |
| 7 | 8 (series), once the questions are answered | series on multi-piece features |

**After each step, re-run and check with the scripts** (numbers from
scripts only):
1. `run_extraction.py` on the 1832 build volumes and the three v2 test
   volumes, written to `output/article_extraction/v3/`.
2. `check_verified.py`: the hand-verified 1832 pages must still match.
3. `evaluating_v1_article_extraction/compare_versions` (`--new v3`):
   nothing logged ok on the 1832 pages may break.
4. `evaluating_v2_article_extraction/evaluate_v2_with_gold.ipynb`
   (`VERSION = "v3"`): the change in exact items, boundary precision and
   recall, titles, front/back matter and issue metadata against the gold
   list.
5. Update the decision's status here: built → checked, with the measured
   change.

**Then:**
- freeze v3 (tag `extraction-v3`);
- run it on the new held-out issues;
- annotate their gold list from the pages;
- score v3 on them.

## Held-out test (2026-11-02)

v3 froze as `extraction-v3` and ran on Penny 1838, Saturday 1834 and Chambers 1843. Scores are in `evaluation/evaluating_v3_article_extraction/v3_gold_comp_eval_summary.md`: 62/76 exact (82%), boundary recall 93%, precision 72%, 27 extra articles. No rule changed after the test texts were opened; the first score is kept as committed. Any gold correction is made from the printed page and listed here, with the corrected score reported beside the first.

Saturday's PDF holds the index to Vol. IV but its issues are Vol. V, so no index was used for it.
