# Article Extraction — v5 Decisions

v5 is the single round of fixes agreed after frozen v4's held-out test (Owen,
2026-11-06). It fixes only bugs and recurring errors found on that test (Penny
1843, Saturday 1843, Chambers 1837), using:
- **results:** `evaluation/evaluating_v4_article_extraction/v4_gold_comp_eval_*`;
- **gold list:** `evaluation/evaluating_v4_article_extraction/gold_article_list_test_v4.csv`.

Owen approved all five fixes (A–E) and asked for v5 to be frozen and scored
once on a new v5 test set. After reading his v4 item notes, he added two more
(F, G).

**How v5 was built:**
- each fix was built, then checked on all twelve seen volumes;
- the checks were the five hand-verified 1832 pages, the v1 reading-order
  log, and the v2, v3 and v4 gold lists;
- every split, drop or caption a fix made in the twelve volumes was listed and
  read before the fix was kept.

**Status:** built and checked 2026-11-06, not frozen yet.

## Results on the seen volumes

The v4 test texts are now build texts, so these scores show that the fixes
worked, not how v5 does on unseen text. The v5 test set gives that.

| | v4 test texts: v4 | v4 test texts: v5 |
|---|---|---|
| Exact items | 95/118 (81%) | 101/118 (86%) |
| Titles | 102/107 (95%) | 108/111 (97%) |
| Front matter in place | 3/7 | 4/7 |
| Back matter in place | 31/43 | 33/46 |
| Series | 1/6 | 2/6 |
| Issue number | 89/107 (83%) | 111/111 (100%) |
| Issue date | 101/107 (94%) | 111/111 (100%) |

- **The v2 and v3 test texts are unchanged** (82/87 and 65/76 exact).
  Saturday 1840 gains one back-matter source ("BROWN.", fix B).
- **The 1832 checks are unchanged:** the five verified pages match, and the
  v1 log comparison is the same.

**After each fix** (v4 test texts):

| After | Exact | Titles | Issue no. | Issue date |
|---|---|---|---|---|
| v4 | 95 | 102/107 | 89/107 | 101/107 |
| A | 99 | 104/109 | 90/109 | 103/109 |
| B | 101 | 105/110 | 91/110 | 104/110 |
| C | 101 | 105/110 | 110/110 | 110/110 |
| D | 100 | 106/110 | 110/110 | 110/110 |
| E | 101 | 107/111 | 111/111 | 111/111 |
| F, G | 101 | 108/111 | 111/111 | 111/111 |

---

## 0. Test texts for v5

**Decision:**
- **Build texts:** the v4 test volumes (`penny_1843`, `saturday_1843`,
  `chambers_1837`) have been seen, so for v5 they become build texts.
- **v5's honest numbers** come from a new held-out v5 test set, which Owen
  builds with its gold list before v5's output is seen. v5 is frozen first and
  scored on it once.

**Status:** decided.

## A. A heading on the last line of a text box

**Decision.** YOLO sometimes boxes the next item's heading with the paragraph
above it ("…tried in this case. / FROGS."). The last line of a text box
becomes a heading box of its own (`split_heading_tails`) when all of these
hold:
1. it is in capitals and follows a finished sentence;
2. it doesn't open with a dash or a footnote mark;
3. it is centred, as headings are, or runs on into the next box on the same
   printed line ("SINGULAR HARE" / "HUNT. A person…");
4. the next box is text (the item's opening), or a title when the line has
   no closing stop ("GENERAL" / "STATE OF STATISTICS.").

**What it leaves alone:**
- **capitals in the middle of a box,** which are section heads ("NORMAN
  DESCENT OF HER MAJESTY.", "THE BOX.");
- **capitals lines set left or right,** which are sign-offs ("CRABBE.",
  "EPICTETUS.").

**Evidence:** Chambers 1837 p15 ("FROGS.", "GENERAL", "SINGULAR HARE");
Penny 1843 p20 ("INSURANCE OF SHIPPING.—"LLOYD'S LIST."").

**Status:** built and checked.
- These four lines are the only splits in the twelve volumes.
- On the v4 test texts, exact went 95 → 99. Two titles are now complete:
  "GENERAL STATE OF STATISTICS" (was "STATE OF STATISTICS") and "SINGULAR HARE"
  (was "HUNT").
- **Known miss:** a heading that opens a box with nothing before it to mark
  an end ("PARODY ON…", Chambers 1837 p31) looks like a section head and
  stays one.
- **Known miss:** Penny's italic run-in "Pekin." has lost its dash in the
  OCR, so it isn't found.

## B. OCR noise at the end of a text box

**Decision.** Document AI sometimes reads stray marks next to a box, from the
margin or a printed line, as its last lines ("…to the Railway Company." /
"19VO"). The noise hides the finished sentence. A printed line under the box
is then taken for a mid-sentence footnote line and ignored (v3, decision 1),
and the next untitled piece is merged.

**The rule** (`strip_junk_tails`): after a finished sentence, up to three
short final lines (at most 4 words) are dropped when each one:
- starts with no capital, quote, bracket, dash or mark;
- doesn't finish a sentence;
- has no comma or semicolon;
- is noise: a word mixing digits and letters ("19VO"), letters outside the
  Latin script, or only words of 4+ letters that the OCR reads nowhere else
  in the volume ("ant oini odord").

Real words that OCR set on a line of their own ("death", "it, and",
"necessities,") occur elsewhere in the volume or carry punctuation, so they
are kept.

**Evidence:** Saturday 1843 p19 ("19VO") and p15 ("enterol el / ed. ૧૦ / ant
oini odord").

**Status:** built and checked.
- Nine boxes in the twelve volumes lose noise lines, all of them real noise,
  including a printer's signature ("2K2").
- On the v4 test texts, Heracleitus (gold 42) is its own article again, and
  exact went 99 → 101.
- In Saturday 1840, "BROWN." is now back matter.
- **Known miss:** a full-width line of real-looking words ("this world of an
  east side boota", Saturday 1843 p11) can't be told from text without a
  dictionary.
- **Known miss:** the untitled piece at the top of a column on Saturday 1843
  p15 has no title or line to mark it.

## C. Penny issues without a masthead (from 1841)

**Decision** (Owen: from the 1841 volume on, the Penny prints its masthead
only at the start of a volume):
1. **Issue start:** "No. N." alone at the foot of a page marks the first page
   of an issue and gives its number (`mark_foot_issue`). It counts as its own
   box, or as the last words OCR joined to the column's last line, and is
   taken out of the text.
2. **Year:** the date is split across facing running heads ("[JANUARY 14," /
   "1843.]"). A date with no year takes the year printed in the issue's own
   running heads.

The rule follows the printed mark, not a year, so it applies wherever a
volume prints its number this way. No other volume in the twelve has a "No. N."
at the page foot.

**Evidence:** Penny 1843 p6, p14, p22 (Nos. 691–693). In v4, "No. 691." was
set aside as a printer's signature, issue 693 wasn't found, and the dates had
no year.

**Status:** built and checked.
- Penny 1843's issue numbers went 0/18 → all correct.
- Its dates are complete ("01-14-1843").
- No other volume changed.

## D. A caption line under a figure stays a caption

**Decision.** A capitals line YOLO drew no box for, directly under or over a
figure that has no caption box, and within the figure's width, is that
figure's caption. Extends v4 rule 1, which covered a line beside a figure.
- **v3's rule doesn't apply to it:** that rule (decision 4) reads an
  all-capitals caption as a title when no title follows ("THE MOLE."). It now
  applies only to YOLO's own caption boxes, not to captions found by their
  place at a figure.

**Evidence:** Saturday 1843 p7, "COLOSSAL STATUE DRAWN TO ITS PLACE." was the
title of a false article.

**Status:** built and checked.
- The false title is gone (titles 105 → 106).
- **Trade-off:** the untitled Epictetus quote under the picture (gold 22)
  now merges into "Egyptian Sculpture" instead of being lost, so exact goes
  101 → 100.
- **Why it still merges:** the printed line under the caption isn't used. A
  line under a caption marks a new item here, but not on Penny 1832 p4, where
  the paragraph after "[Horns of the Wapiti.]" is the same article (v1 log).
  So the v2 rule that ignores lines under captions stays.

## E. A title with a footnote mark is not a footnote

**Decision.** A box opening with a capitals title that carries a footnote mark
("MANAGEMENT AND MISMANAGEMENT.* GREAT men have written…") is a title and
text. The mark points to a footnote; it doesn't open one.
- **The printed line above it** marks a new item, not a footnote line.
- **Run-in heads** may carry the mark after their stop.

**Evidence:** Chambers 1837 p30: the article was taken as a footnote and lost.

**Status:** built and checked.
- The article is found with its title and its footnote ("* Education Reform,
  by Thomas Wyse…").
- On the v4 test texts, exact went 100 → 101 and titles 106 → 107.

## F. Numbered sections are sections, never the title

**Decision** (Owen): sections stay sections. The Saturday 1843 supplement
should read:
- **series:** "A Brief History of the Fine Arts" (part VIII);
- **title:** "The History of Copper-Plate Engraving.—Concluded";
- **first section:** "Section 1. Early British Engraving", as front matter.

The rules:
1. **Joining:** a "SECTION N." (or "CHAPTER N.") box joins the heading box
   under it, giving "SECTION 1. EARLY BRITISH ENGRAVING." (`join_section_numbers`).
2. **Sections:** a "SECTION N. …" heading is a section, never the article's
   title.
   - Directly under the title it is front matter and the first subsection,
     as with Iona in v4.
   - Later in the article it stays in the text and is listed in the
     subsections. It opens no new article.
3. **Series:** a caption printed with the picture before the title and
   carrying a part number ("A BRIEF HISTORY OF THE FINE ARTS. VIII.") is the
   series leader: the series and its part (`caption_leader`). It stays the
   caption too. A caption with no number ("HEREFORD CATHEDRAL.") is only a
   caption.

**Evidence:** Saturday 1843 PDF p21–28 (gold 47). v5 before this read the
title as "SECTION 1. EARLY BRITISH ENGRAVING" and the series as "The History of
Copper Plate Engraving Concluded".

**Status:** built and checked.
- Title, front matter and series now match the gold.
- The subsections read "SECTION 1. EARLY BRITISH ENGRAVING; SECTION 2.
  ENGRAVING ON MONUMENTAL BRASSES; …" through Section 10.
- "SECTION N." appears in no other volume, and no other article changed.

## G. Longer "From…" sources

**Decision** (Owen): expand the word limit for back matter. A dash sign-off
opening "From" can be up to 25 words and can name a work in quotes. It must
name something: at least 2 capitalised words after "From". So "—From that day
he never spoke again." is not a source.

**Evidence:** Chambers 1837 gold 81, "—From a forthcoming work by Dr Busham
of Dumfries, entitled "The Philosophy of Instinct and Reason."" Before this it
was left in the text, being over the 12-word limit for dash sources.

**Status:** built and checked.
- Chambers 81's source is back matter, and no other article changed in the
  twelve volumes.
- **Known miss:** Chambers 88, "…remarkable for longevity. From Observations on
  the Preservation of Hearing, by J. Harrison Curtis.", has no dash in the
  OCR, so it reads as a final sentence.

## Checked against Owen's v4 item notes (2026-11-06)

Owen's item notes on the v4 gold list describe how each item's titles,
sign-offs, printed lines and footnotes appear. Read against the rules, they
confirm these conventions:
- **captions:** captions stay captions;
- **printed lines:** a line proves a new item, but a missing line proves
  nothing (Chambers' miscellany pages have none);
- **sign-offs:** they come at the end of the text, after a dash;
- **Penny 1843 titles:** italic run-in titles with a dash;
- **footnotes:** a footnote belongs to the article carrying its mark, not
  the nearest one;
- **supplements:** the Iona convention for supplement sections.

Two questions were settled:
- **Series vs continuation stays as built (rule 3, v4).**
  - "On Dioramic Painting. II. Portable Diorama" is a continuation, not a
    series, because its theme carries on. It is an accepted edge case and
    miss.
  - "Public Improvements.—No. II., Provincial Towns." stays a series.
- **A printed line under a caption doesn't count as an item rule.**
  - Penny 1832 p4: the paragraph after "[Horns of the Wapiti.]" is the same
    article.
  - An article can have a captioned picture with a line inside a column,
    mid-article.
  - The Saturday 1843 p7 line under the caption that does end "Egyptian
    Sculpture" is accepted as a miss (see fix D).

---

## Known limitations carried forward

- **Section headings inside articles.** A section heading YOLO boxed as a title
  can split an article (Chambers 1837 "ENGLISH AND FRENCH.", "5. DRESSING FOR
  COMPANY.", "FRANCE. BERANGER."). There is no general subsection rule.
- **Untitled pieces with no printed signal** (no title, no line, no closing
  sign-off before them) merge into the item before.
- **Garbled series names:** OCR of decorative series headings (Saturday 1843
  "Royal Residences of Scotland").
- **Some sources are missed:** short sources with no dash ("Milner.",
  "Guizot."), and "From…" sources whose dash OCR lost.
- **Lost items:** Saturday's chess problems and the end-of-volume notice.

## Next

1. Freeze v5: tag it `extraction-v5`, then run the v5 test set with the tagged
   code.
2. Owen builds the v5 test set and its gold list from the printed pages.
3. Run frozen v5 once on it and score it. Then add v5 to `FROZEN_VERSIONS`.
4. Apply v5 to all volumes. Later errors are known limitations.
