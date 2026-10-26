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

**v2 baseline** (85 gold items):
- 72% exact; boundary recall 93%; boundary precision 64% (44 extra pipeline
  articles);
- titles 81%; back matter in place 58%; front matter in place 13%;
- Chambers issue numbers and dates 0%.

**Open questions (Owen):**
1. **Decision 0:** do the v2 test volumes become v3 build texts, with v3's
   real numbers from a new set of held-out issues?
2. **Decision 8b:** are numbered titles ("On Garden Herbs. I.") series
   parts?
3. **Decision 8a:** do the test volumes' indexes group pieces under a series
   heading? This decides whether the index can supply series.

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

**Status:** proposed.

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

**Evidence.**
- 19 of the 44 extra articles were started by a printed rule; 16 of those
  start mid-sentence, 13 of them in Chambers ("are bound together…",
  "dustrious habits…", "grapher of Johnson…").
- Example: `chambers_1839` PDF p7 → p8 (check images
  `chambers_1839_page_007_order.jpg` / `_008_order.jpg`).
  - Living in Paris ends p7's right column with "…by which young men", above
    a footnote rule and "* The French pound is…".
  - p8 continues "are bound together in London…", but as article 4.

**Status:** proposed.

## 2. Chambers 1840 masthead

**Decision.**
- **Issue number:** "NUMBER 414" counts like "No. 414", for reading the
  number and recognising the masthead.
- **The masthead band:** on an issue's first page, the row of short boxes
  across the top above the first title (number, date, price, printer, the
  editors' line) is all masthead, read across the columns, not column by
  column.
- **Chambers config:** add "editors of" to Chambers' masthead wording.

**Evidence.**
- `chambers_1839` PDF pp. 7, 15, 23: "NUMBER 414.", "SATURDAY, JANUARY 4,
  1840.", "PRICE THREE HALFPENCE.", "PRINTED BY BRADBURY AND EVANS…" and "BY
  WILLIAM AND ROBERT CHAMBERS, EDITORS OF…" became titles, series headings
  and articles.
- These account for about 10 extra articles and 3 wrong titles, and split
  each issue's first article (Living in Paris into four).
- Chambers issue number and date: 0% (39 items).

**Status:** proposed.

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

**Status:** proposed.

## 4. Captions taken as titles

**Decision.** An all-capitals YOLO caption becomes a title only when no title
box follows before the text. Otherwise it stays the illustration's caption.
The v1 rule was made for "THE MOLE.", which has no title of its own.

**Evidence.**
- "FLOATING TIMBER IN LOMBARDY" for The Timber-Floats of Germany and Italy
  (Saturday gold 30).
- "RUINS OF THE ABBEY OF ST. BERTIN…" for St. Omer's, in France (gold 42).

**Status:** proposed.

## 5. Generic headings taken as titles

**Decision.** A heading that only says "Introduction", "(First / Second / …)
Article", "Continued" or "Concluded" is front matter (a continuation note
where it says so), not the title.

**Evidence.**
- "INTRODUCTION" for On Garden Herbs. I. (Saturday gold 48).
- "SECOND ARTICLE" for Speculation on Words (Chambers gold 87; also front
  matter of M. Turgot, gold 80).

**Status:** proposed.

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

**Status:** proposed.

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

These should be low-risk. The signals (foot of the column, a rule above,
small type) are how footnotes are printed in all three magazines.

**Evidence.** Chambers gold 52, 54, 65, 67, 84, 86 (wrong article), 87 (lost
mark); p7 (both corners handled, but see decision 1). Also 5 footnotes left
in the text in Penny and Saturday (Penny gold 5, 17; Saturday 31, 33):
check whether (b) catches them.

**Status:** proposed.

## 8. Series over several pieces; numbered titles

**Decision.**
- **(a) One heading over several pieces:** use the volume index, if the
  test indexes list the pieces under the series heading (as Penny 1832's did
  for British Animals). No page-layout rule (see v2 decision 3: it would
  misfire).
- **(b) Numbered titles:** decide whether "On Garden Herbs. I." is a series
  part (v2) or not (the gold list). Then align the pipeline or the gold
  convention.

**Evidence.**
- "Remarkable Cases of Circumstantial Evidence" over 5 Chambers pieces (gold
  81–85; only the first gets it).
- "National Galleries for the Fine Arts at Munich" (Penny gold 4, 13).
- "Last Century Anecdotes" (Chambers gold 67–68).
- Numbered titles flagged "extra series": Saturday gold 31, 42, 43, 48;
  Penny 14; Chambers 87.

**Status:** (a) proposed; (b) to decide (Owen).

## 9. Smaller items (known limits unless cheap)

- **Issue numbers misread:** Penny 271 read as "10", 270 not read; Saturday
  484 not read. Check whether the masthead fix (2) and the issue sequence
  check cover these.
- **Running head inside a figure box:** a Saturday figure box that includes
  the running head ("THE SATURDAY MAGAZINE. 1840.]") starts an extra
  article (3 cases).
- **Front matter written as prose or verse** (epigraphs, editor's
  introductions: Saturday gold 27, 33, 48; Chambers 57) stays in the text.
  Known limit without italics.

**Status:** noted.

---

## Build order and checks

**Order: biggest gain and lowest risk first.**

| Step | Decisions | Expected effect (v2 test volumes) |
|---|---|---|
| 1 | 1 (rules mid-sentence) + 7 (footnotes) | about 16 fewer extra articles; Chambers footnotes on the right article |
| 2 | 2 (Chambers masthead) | about 10 fewer extra articles; 3 titles right; Chambers issue numbers and dates read |
| 3 | 3 (`abandon` content) | 3 lost poems recovered |
| 4 | 4, 5 (captions, generic headings) | about 4 titles right |
| 5 | 6 (sign-offs) | up to 14 sources moved from the text to back matter |
| 6 | 8 (series), once the questions are answered | series on multi-piece features |

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
