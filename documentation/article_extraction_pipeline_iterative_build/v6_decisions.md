# Article Extraction — v6 Decisions

v6 fixes how issues are found and recorded, after frozen v5's held-out test
(Penny 1844, Saturday 1837, Chambers 1840; `v5_decisions.md`, "Held-out
test"). On that test, issue numbers were right for only 14 of 80 items. The
cause was three masthead forms, each repeating in every issue of a volume
printed that way. Owen approved the fixes on 2026-11-10.

**What v6 changes:**
- **Metadata:** issue starts, numbers, dates and the masthead record.
- **One case-test fix** that the corrected issue starts exposed (fix 6).
- **Nothing else:** no rule for article boundaries, titles or front and back
  matter changed.

**Status:** built and checked 2026-11-10, not frozen. Owen wants no further
held-out run for now.

## Results

- **Issue starts:** all fifteen seen volumes now find exactly three issues,
  each with its right number. Each fix was checked on all fifteen against the
  five verified pages, the v1 log and all four gold lists.

| Volume | v5 issue numbers | v6 issue numbers |
|---|---|---|
| Penny 1844 | 755, **4** (false start p9), 756, 757 | 755, 756, 757 |
| Saturday 1837 | none found (one issue) | 291, 292, 293 |
| Chambers 1840 | blank, blank (third issue missed) | 105, 106, 107 |
| the other 12 volumes | right | right (unchanged) |

- **On the v5 test texts,** which are now seen, so these are not held-out
  numbers:
  - issue numbers 14/80 → 80/80, and issue dates 47/80 → 80/80;
  - exact items 68 → 69 (Chambers "Literary Formulas" is no longer split at
    the missed issue start);
  - series 5/13 → 6/13, and illustrations 75 → 78.
- **The v2, v3 and v4 gold scores are unchanged.** So are the verified pages
  and the v1 log. Apart from the masthead record, the article and page
  tables of the twelve earlier volumes are identical.

---

## 1. Picture boxes over the masthead: no word limit

**Decision.** A box only counted as masthead if it had 40 words or fewer (a
long article opening isn't a masthead). But when YOLO boxes the masthead
together with the picture under it, most of that box's words are OCR noise from
the engraving. Saturday 1834 (30 words) and 1840 (34) passed by chance;
Saturday 1837 (52, 61) didn't. A picture box in the top third of the page now
marks an issue start whatever its length, when it holds:
- masthead wording ("PRICE ONE PENNY", "UNDER THE DIRECTION"); or
- the magazine's own issue-number form together with its masthead words
  ("No 292." with "ONE PENNY.").

OCR breaks these forms inside the picture ("SPRICE enco … ONE PENNY", "N№ 293.").

**Status:** built and checked. Saturday 1837 finds Nos. 291–293. The OCR lost
291's printed number, so it comes from its neighbours (292, 293).

## 2. A magazine name inside a tall picture is not a masthead

**Decision.** The magazine's name in large type marks an issue start. A tall
picture box that swallowed the running head ("THE PENNY MAGAZINE.", Penny 1844
p9) passed that test. Owen: a running head on a page that doesn't start an
issue is always furniture, even above a picture. In a picture box, the name now
counts only if:
- the box is masthead-sized (under 30% of the page height); or
- it carries other masthead wording ("Society for the Diffusion…").

**Status:** built and checked. The false issue on Penny 1844 p9 (numbered "4"
from the page number) is gone.

## 3. A bare Roman numeral can be the issue number

**Decision.** A masthead box holding only a Roman numeral of at least two
letters ("CV.", "CVII.") is the issue number. Chambers 1840 prints it this
way. "I." or "V." alone doesn't count. This adds to v5 fix H, which needs
"No." or "NUMBER" before the numeral.

**Status:** built and checked. Chambers 1840 reads Nos. 105–107.

**Flagged for later (Owen):** this Chambers volume is an American reprint.
Its masthead gives "Two Dollars per Annum", it is numbered 105–107 on the
dates of the Edinburgh Nos. 414–416, and its articles differ. Which edition
the corpus uses is to be decided.

## 4. "EDINBURGH OURNAL"

**Decision.** The large-type masthead name test accepts "EDINBURGH JOURNAL" with
the J lost by OCR.

**Status:** built and checked. Chambers 1840 p24 starts its issue.

## 5. The 8-page issue rhythm

**Decision** (Owen): a new issue starts every 8 pages, virtually without
exception. Once an issue start is known, the next is 8 scanned pages later
(Saturday 1837 p5, 13, 21). Duplicate scan pages don't count. The rules
(`issue_rhythm`):
- **Drop:** a start found only by the magazine's name, and not 8 pages after
  the previous start, is dropped.
- **Fill:** a run of more than 8 pages with no start gets a start 8 pages on,
  if that page's printed number, when read, is a first page (1, 9, 17, …).
- **Keep:** a start found by masthead wording or a foot number is kept
  wherever it falls. Penny 1838's monthly supplement starts 4 pages after
  the issue before it.

**Status:** built and checked. With fixes 1–4 every start is found directly,
so the rhythm didn't need to fire in any of the fifteen volumes. It is a
safety net for the full run.

The pages table has a new column, `issue_evidence`, recording what marked each
start: masthead wording, magazine name, issue number at the foot, or the
8-page rhythm. A start that was dropped records why.

## 6. "No." in a capitals heading is not mixed case

**Decision.** A capitals heading carrying "No. XX." is still a capitals heading.
Before this, the lowercase "o" made "'ESSAYS ON THE LIVES OF REMARKABLE
PAINTERS.—No. XX.*" (Penny 1844 p9, opening with a stray quote mark) look like
a quotation inside an article (v3, decision 10).

**Why it showed only now:** v5's false issue start on p9 had hidden this
fault.

**Status:** built and checked. The series is found again. Nothing else
changed.

## 7. The masthead record keeps masthead lines inside a picture box

**Decision** (Owen): Saturday's masthead changes on 21 January 1837. From then on
it drops "UNDER THE DIRECTION OF THE COMMITTEE OF GENERAL LITERATURE AND
EDUCATION, APPOINTED BY THE SOCIETY FOR PROMOTING CHRISTIAN KNOWLEDGE". This is
part of the magazine's editorial history, so the `masthead_text` column must
show it.
- **The gap:** when the masthead is inside a picture box, its lines weren't
  recorded.
- **Now** (`picture_masthead_text`): they are recorded, from the box's top
  line down to the last line with masthead wording. The picture's noise below
  is left out.
- **A name alone is not a masthead:** a picture box that holds only the
  magazine's name (the running head on Penny's later issues) records nothing.

**Status:** built and checked. The masthead record now shows:
- **Saturday 1834 Nos. 138–140 and 1837 No. 291:** the Committee and Society
  line is present.
- **Saturday 1837 Nos. 292–293:** it is absent.
- **Saturday 1840:** absent.

Only the `masthead_text` column changed in the other volumes' page tables.

---

## Next

1. **Freeze v6:** commit, then tag `extraction-v6`. Owen will decide whether
   to run another held-out test or go straight to all volumes.
2. **Still open from the v5 test,** to be logged as known limitations:
   - Penny's run-in titles merging (Hudibras / Practical Philosophy);
   - articles with verse splitting;
   - two Chambers 1840 articles lost;
   - Saturday 1837 "The Alligator", whose title is inside the masthead
     picture box and garbled by OCR.
