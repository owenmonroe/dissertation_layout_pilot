# Article Extraction — v4 Decisions

These are the changes for v4. They come from scoring frozen v3 against the
gold article list of the v3 test volumes (Penny 1838, Saturday 1834,
Chambers 1843), using:
- **results:** `evaluation/evaluating_v3_article_extraction/v3_gold_comp_eval_*`;
- **gold list:** `evaluation/evaluating_v3_article_extraction/gold_article_list_test_v3.csv`;
- **guide:** `gold_article_list_annotation_guide.md`.

Each entry gives the decision, the evidence (volume and PDF page) and the
measured result, in the same format as `v3_decisions.md`.

**How v4 was built (2026-11-03 to 2026-11-06):**
- **One rule at a time:** Owen decided each rule before it was built, and each
  rule was checked on all nine seen volumes before moving to the next.
- **Rules follow printing conventions** and must generalise to many more,
  more complex volumes. A miss that only one page shows stays a known miss.
- **Chambers 1843 p9** is a badly distorted scan and did not drive any rule.

**Status:** all six rules are built and checked. v4 is frozen as
`extraction-v4` (commit `48e6222`) and was run once on the held-out v4 test
texts (see "Held-out test" at the end).

## Output conventions settled for v4 (Owen)

- **Issue dates are numeric:** `MM-DD-YYYY`, or `MM-YYYY` for an issue dated by
  month only (a monthly supplement). Month names are not written out.
- **Captions stay captions.** An illustration caption is never a title or
  front matter. A full-page picture's caption ("HEREFORD CATHEDRAL") is a
  caption, and the article's title follows with its text.
- **Dashes:** a dash can appear in text, titles and front matter. It is a
  sign-off only at the end of an article.

## Results on the seen volumes

These scores are on texts that v4's rules were written from, so they show
that the fixes worked, not how v4 does on unseen text. The v4 test texts give
that.

**v3 test texts** (76 gold items, 74 scored; corrected v3 gold list):

| | v3 (frozen rules) | v4 |
|---|---|---|
| Exact items | 62 (82%) | 65 (86%) |
| Split | 11 | 8 |
| Merged | 2 | 2 |
| Lost | 1 | 1 |
| Boundary recall | 97% | 97% |
| Boundary precision | 74% | 83% |
| Extra pipeline articles | 25 | 15 |
| Pipeline articles | 98 | 89 |
| Titles | 65/74 (88%) | 72/74 (97%) |
| Front matter in place | 8/12 (67%) | 10/12 (83%) |
| Back matter in place | 51/74 (69%) | 59/74 (80%) |
| Footnotes in place | 28/37 | 34/37 |
| Series (where either has one) | 2/10 (20%) | 7/9 (78%) |
| Continued from | 72/74 | 73/74 |
| Illustration count | 69/74 | 71/74 |
| Issue number | 100% | 100% |
| Issue date | 73/74 | 74/74 |

**v2 test texts** (87 gold items): exact stays at 82/87 (94%), and every
other score is unchanged except:
- back matter in place, 55/66 → 57/66;
- footnotes in place, 30/36 → 31/36.

**1832 build pages:**
- the five hand-verified pages match after every rule (`check_verified.py`);
- the comparison with the v1 reading-order log (`compare_versions.py --old v1
  --new v4`) is unchanged after every rule.

**Score after each rule** (v3 test texts):

| After | Exact | Extras | Titles | Front matter | Back matter | Series | Issue date |
|---|---|---|---|---|---|---|---|
| v3 rules | 62 | 25 | 65 | 8/12 | 51 | 2/10 | 73 |
| rule 1 | 62 | 23 | 66 | 8/12 | 51 | 2/10 | 74 |
| rule 2 | 64 | 18 | 66 | 8/12 | 51 | 2/10 | 74 |
| rule 3 | 64 | 17 | 71 | 10/12 | 51 | 6/9 | 74 |
| rule 4 | 65 | 15 | 72 | 10/12 | 54 | 7/9 | 74 |
| rule 5 | 65 | 15 | 72 | 10/12 | 57 | 7/9 | 74 |
| rule 6 | 65 | 15 | 72 | 10/12 | 59 | 7/9 | 74 |

---

## 0. Test texts for v4

**Decision:**
- **Build texts:** the v3 test volumes (`penny_1838`, `saturday_1834`,
  `chambers_1843`) have now been seen, so for v4 they become build texts,
  alongside the 1832 volumes and the v2 test volumes.
- **Development scores:** all nine volumes are still scored at each step,
  against both gold lists.
- **v4's honest numbers** come from a new held-out set, which Owen built
  with its gold list and item notes before v4's output was seen
  (`evaluation/evaluating_v4_article_extraction/`). It includes a
  supplement.

**Gold correction (from the printed page):** the Saturday 1834 PDF p8 heading
reads "No. III." (was "No. II."), changed in
`gold_article_list_test_v3.csv` and `.numbers`.

**Scorer:** `score_gold.py` reads both the new numeric dates (`08-30-1834`,
`08-1834`) and the gold's `8.1834`.

**Status:** done.

## 1. Mastheads, front-page pictures and month-only dates

**Decision.** Four faults, each on an issue's first page:
1. **Supplement mastheads:** "supplement" counts as masthead wording, shared
   by all magazines ("MONTHLY SUPPLEMENT OF").
2. **Masthead inside a picture box:** when a figure box at the top of an
   issue's first page also holds masthead text, the title is read only from
   the text after the last masthead line. A masthead picture whose page has
   no article text gives no title.
3. **Front-page picture and caption:** a capitals line with no YOLO box,
   level with a figure and within 60 px of its sides, is a caption
   (`beside_figure`). It stays a caption, not a title or an article.
4. **Month-only dates:** an issue dated "SUPPLEMENT FOR AUGUST, 1834." gets
   the date `08-1834`. All dates are written as numbers (see the
   conventions above).

**Evidence:**
- `penny_1838` PDF p18, No. 433: the supplement masthead was read as an article.
- `penny_1838` PDF p14, No. 432: title "PUBLISHED EVERY SATURDAY", should be
  Laborde.
- `saturday_1834` PDF p5, No. 138: "HEREFORD CATHEDRAL" was a 0-word article.
- `saturday_1834` No. 139: no date.

**Status:** built and checked.
- All four are fixed. On the v3 test texts, extras went 25 → 23, titles
  65 → 66, issue dates 73 → 74 and illustration counts 69 → 70.
- **Problem found in the check:** the first version took "INFANT ACADEMY;
  AFTER SIR JOSHUA REYNOLDS" (`saturday_1840` PDF p6, a full-page picture
  caption) as a title. This is why the rule now needs article text on the
  page.

## 2. Supplements

**Decision.** A monthly supplement is one long article with sections:
1. **Spotting one:** its masthead or running head says "SUPPLEMENT".
2. **Headings inside a supplement** are subsections of the current article.
   They stay in the text and are also listed in `subsections`.
3. **New articles:** a new article starts only after a printed rule, an
   article's close, an editorial notice or the imprint.
4. **New column:** every article gets a `supplement` column (yes/no).
5. **Check:** the run prints "supplement check: No. X has N articles" when a
   supplement still yields more than one article, since several articles in
   one supplement are rare.

**Evidence:** the gold makes all three supplements in the seen volumes one
article:
- Penny No. 272 (1836), "The Tower of London": already one;
- Penny No. 433 (1838), "Public Improvements": 3 pieces;
- Saturday No. 139 (1834), "Sketches of the Highlands": 5 pieces (Iona,
  Staffa, Mull, Arisaig, Small Isles).

**Status:** built and checked.
- Saturday No. 139 is one article, PDF p13–20, with `subsections`
  STAFFA; MULL; ARISAIG…; SMALL ISLES. EGG.
- Penny 433 became one article after rules 3–4.
- On the v3 test texts, exact went 62 → 64 and extras 23 → 18.
- No weekly issue changed.

## 3. Numbered headings: series parts and continuations

**Decision** (Owen's convention):
- **Series part:** "No. N." with a subject of its own under a heading
  marks a part of a series ("PUBLIC IMPROVEMENTS. —No. II., PROVINCIAL
  TOWNS."). The heading is the series and N its part.
- **Continuation:** a number with no other title, the same title
  numbered I, II, …, is a continuation.
- **Both** can apply to one article.

The rules:
1. **"No. N." under a heading:** a line opening "No. N." with its own
  subject, directly under a heading, is the title ("No. V. LITTLE
  MUSGRAVE…"). The heading above is the series, and N is `series_part`.
2. **On one line:** a single line with name, "No. N." and subject is the
  title in full. The name is the series.
3. **Number in the leader:** a leader that carries its number ("ON WILLS.
  No. IV") gives the series "On Wills", part IV.
4. **"PART THE SECOND." under a title** is front matter. It means part 2
  and `continued_from` the earlier part, not a series.
5. **Dashes:** a "—No. N." inside a heading is never a sign-off.
6. **Broken words:** a word broken across lines in a series name is joined
  ("EXPERI- MENTAL").

**Evidence:**
- `penny_1838` PDF p6 (English Romantic Ballads No. V) and PDF p18 (Public
  Improvements No. II);
- `saturday_1834` PDF p8 (Mines of Great Britain No. III), PDF p10 (On Wills
  No. IV), PDF p14 (Sketches… Part the Second) and PDF p27 (Familiar
  Illustrations of Experimental Science No. IV).

**Status:** built and checked.
- All six read as the gold has them.
- On the v3 test texts, titles went 66 → 71, series 2/10 → 6/9, front
  matter 8/12 → 10/12 and extras 18 → 17.
- **Why the series score rose:** v3 only found a series from a recurring
  leader printed on its own line. These test texts mostly print the number
  with the heading, and v3 took the series name as the title.

## 4. Footnote marks and section marks

**Decision:**
1. **More footnote marks:** a box opening with "•" or "+" is a footnote,
   like `* † ‡`, because OCR often reads `*` as these. A plain period "."
   is never read as a mark.
2. **Section headings:** "§ N. …" is a section heading, not a footnote. It
   stays in the text and is also listed in `subsections`. It is checked
   before the front-matter tests, so it is never taken as a byline or
   subtitle.
3. **Supplement front matter:** a supplement's opening section heading
   ("IONA; INSULAR CHURCHES.") stays front matter and is also listed first
   in `subsections`. Owen's reason: dropping it from front matter could
   weaken the subtitle-as-front-matter handling in ordinary articles.

**Evidence:**
- Five boxes across the nine volumes open with "•" or "+", and all five are
  footnotes: `penny_1836` p27, `penny_1838` p11, `saturday_1834` p6, p8 and
  p22.
- `saturday_1834` PDF p10, On Wills: "§ 7." was taken as a footnote,
  which split the article.

**Status:** built and checked.
- The five footnotes are now back matter.
- On Wills is one article again, with § 6 and § 7 in `subsections`.
- On the v3 test texts, exact went 64 → 65, extras 17 → 15, titles 71 → 72,
  back matter 51 → 54 and series 6/9 → 7/9.
- **Problem found in the check:** "§ 6." was first caught as centred front
  matter. That is why section headings are now checked first.

## 5. Footnotes inside a text box

**Decision.** Sometimes YOLO boxes a footnote together with the paragraph
above it.
1. **Built:** the footnote is cut from the foot of the text box and becomes
   back matter of its article (`split_footnote_tails`). All of these must
   hold:
   - a line near the end opens with a mark and a capital (`* † ‡ • +`);
   - it has at least 3 lines above it in the box;
   - it is at most 8 lines long to the box's end;
   - its type is smaller than the lines above (median line height under
     0.92 of theirs).
2. **Owen's condition:** a footnote with no detectable mark should become
   back matter of the nearest article in its column, but it must not
   break up existing text or articles.

**Evidence:** the six footnotes cut:
- `chambers_1843` p11 and p29;
- `penny` p19 (1832);
- `penny_1838` p14 and p16;
- `saturday_1840` p19 ("* Nahum, ch. i. v. 8.").

**Status:** part 1 built and checked.
- All six are cut, and no article boundary or title changed in any volume.
- On the v3 test texts, back matter went 54 → 57. On the v2 test texts it
  went 55 → 56.
- **Problem found in the check:** the play cue "* AIR, Ally Croaker."
  (`chambers_1839`) was cut. That is why at least 3 lines are needed above
  the mark.

**Tried and dropped:** finding footnotes that lost their mark by their place
at the foot of a column, in small type. In the check, it:
- took two poems in `saturday_1840` and the editorial notice on
  `chambers_1839` p30;
- missed the footnotes it was meant for;
- dropped `saturday_1840` exact items.

That broke Owen's condition, so the rule was removed. Owen accepts that
some footnotes are missed like this. The known misses are:
- `penny_1836` p23 (Hentzner);
- `penny_1838` p12 ("Alluding…") and p19 ("HPictorial…", its `*` read as
  "H");
- `saturday_1834` p14 ("The practice alluded…").

## 6. Sign-offs and sources at the end of Chambers paragraphs

**Decision.** Owen: catching the sources at the end of Chambers paragraphs
("—Bentley's Miscellany.") is very important. Small initials ("H.", "A. C.")
may sometimes be missed. This step checked why sources were missed and
fixed only bugs:
1. **Dashes as OCR reads them:** a sign-off dash may be one to three
   characters ("-", "--", "---", "—") or a dash look-alike ("–", "‒", "―",
   "−", "⸺", "⸻"). This is still read only at the very end of an article's
   text, before a capitalised source. "_" and "~" are not accepted. Across
   the nine volumes they would catch only one box, the scrambled "Binns on
   Sleep", and record a wrong source.
2. **Hyphenated words** are allowed in a source with no dash
   ("Self-Culture").

**Evidence:**
- `chambers_1843`: "---Scottish Jests and Anecdotes." and "---Bentley's
  Miscellany.";
- `chambers_1839`: "Dr Channing's Pamphlet on Self-Culture."

**Status:** built and checked.
- The three sources are now back matter, and nothing else changed.
- On the v3 test texts, back matter went 57 → 59. On the v2 test texts it
  went 56 → 57.
- The dash look-alikes changed no output in the nine volumes; they are a
  guard for new volumes.
- **Problem found in the check:** the first hyphen fix let a source run back
  over earlier sentences. That lost "Elliot's Letters…" and "Cobbett's
  Cottage Economy" in the 1832 Chambers. Hyphen pieces can no longer
  contain "." or ",".

**Known misses:**
- "Binns on Sleep", "Naval and Military Gazette" and "Man the Reformer":
  OCR mixed the words with the next column.
- "…his. Newspaper paragraph.": no dash, and it reads as an ordinary
  short sentence.
- Small initials were not looked at, as agreed.

---

## Still wrong on the v3 test texts after v4

- **Splits (8):** Chambers 1843 gold 2, 3, 6, 8 and 27; Saturday 1834 gold
  53 and 68; Penny 1838 gold 77. These are mostly inner headings or
  quoted matter read as new articles, which have no general rule (Owen,
  2026-11-02).
- **Merged (2):** Chambers 1843 gold 34 and 35 (Agriculture in England /
  The Walhalla).
- **Lost (1):** Penny 1838 gold 84.
- **Titles broken over two lines:** "Rural and Domestic Life / In Germany"
  and "The Forbidden Fruit / or, Eve's Apple Tree of Ceylon". The first line
  is taken as a series, and the second as the title.
- **Title missing:** Chambers 1843 gold 1 ("Tact."), on the distorted p9.

## Next

1. Freeze v4: add v4 to `FROZEN_VERSIONS`, set `PIPELINE_VERSION = "v5"`,
   and tag it `extraction-v4`. Owen commits and pushes.
2. Run frozen v4 once on the v4 test texts, and score it against the v4
   gold list.
3. Review the results with Owen's item notes, to check the assumptions about
   titles, sign-offs, printed lines and footnotes.
4. If the results are good, apply v4 to all volumes. If not, make one round
   of fixes for bugs and recurring errors only, then run all volumes. Any
   later errors are logged as known limitations.

## Held-out test (2026-11-06)

Frozen v4 (`extraction-v4`) ran once on Penny 1843 (Vol. XII), Saturday 1843
(Vol. XXIII) and Chambers 1837 (Vol. VI), three issues each. These texts
were not opened while v4 was built.
- **Setup:** only the three volumes were added to `magazine_rules_config.py`.
  `score_gold.py` reads the v4 gold's `figure_notes` and `item_notes` columns
  in place of `notes`. No rule changed.
- **Gold corrections from the printed page:**
  - Penny issues 692–693 are dated 1843 (they were entered as 1834);
  - Chambers No. 272 is dated April 15, 1837 (it was entered as 4.16);
  - Chambers gold 81 opens "The actions of the" (it was entered as "The
    sections of the").
- **Scorer fix:** an item's first words can also appear earlier on the page,
  quoted inside another article ("It is well known that…" in Interesting
  Botanical Experiment, then opening Hydrostatic Bed, Chambers p15). An
  equally good match at an article's start now wins. This changed 4
  Chambers items from merged or split to exact (65, 66, 81, 95). It
  changed nothing in the v2 or v3 gold scores, including frozen v3's
  held-out score.

Scores are in `evaluation/evaluating_v4_article_extraction/v4_gold_comp_eval_summary.md`:

| | Penny 1843 | Saturday 1843 | Chambers 1837 | All |
|---|---|---|---|---|
| Gold items | 20 | 26 | 72 | 118 |
| Exact | 16 (80%) | 17 (65%) | 62 (86%) | 95 (81%) |
| Merged / split / lost | 4 / 0 / 0 | 6 / 0 / 3 | 4 / 5 / 1 | 14 / 5 / 4 |
| Boundary recall | 90% | 77% | 96% | 91% |
| Boundary precision | 100% | 74% | 90% | 88% |
| Titles | 16/18 | 18/20 | 68/69 | 102/107 (95%) |
| Back matter in place | 6/9 | 5/7 | 20/27 | 31/43 (72%) |
| Front matter in place | – | 1/2 | 2/5 | 3/7 |
| Series | 1/1 | 0/3 | 0/2 | 1/6 |
| Issue number | 0/18 | 20/20 | 69/69 | 89/107 |
| Issue date | 12/18 | 20/20 | 69/69 | 101/107 |
