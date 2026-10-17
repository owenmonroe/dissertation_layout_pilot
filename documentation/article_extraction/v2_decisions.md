# Article Extraction — v2 Decisions

Decisions and new rules from the v1 development evaluation (`v1_evaluation.md`,
log `evaluation/reading_order_error_log.csv`). Each entry gives the decision,
the evidence (magazine, page, box from the log), and its status.

**Status key:** `decided` (agreed, not built) → `built` (in the code) →
`checked` (re-checked against the development log). Update the status here as
v2 is built; `v1_rules.md` stays as it was.

---

## 0. Versioned output (built 2026-10-16)

**Decision.** Keep each version's output apart, so the v1 output the
evaluation log describes is never overwritten.
- `output/article_extraction/<version>/`;
- `run_info.json` per magazine;
- a `pipeline_version` column;
- `FROZEN_VERSIONS` guard;
- the template script takes `--version`.

v1's output was moved unchanged into `v1/`. The only edit was its figure paths
(`regions.image_file`), updated to follow the move. A first v2 run (rules not
yet changed) matched v1 exactly apart from the version column and figure
paths.

**Status:** built.

## 1. Front matter and back matter

**Decision.** Replace `title_note`, `byline`, `attribution` and `end_note`
with two article fields and two box roles, decided by **position**, not by
kind of line. The magazines put sources and authors at either end, so where a
line sits is what's meaningful.

- `front_matter`: everything between the title and the first paragraph:
  source lines ("[From a Correspondent.]", "FROM THE REV. WILLIAM JONES."),
  bylines, subtitles ("AN ENGLISH TALE, BY MISS MITFORD."), epigraphs ("My
  Library / Was Dukedom large enough." —Prospero), quoted sayings the article
  expounds ("FATHERS HAVE FLINTY HEARTS."), feast dates ("[July 15th.]"),
  editorial headnotes, continuation notes ("Concluded from No. I.").
- `back_matter`: everything after the last paragraph: sign-offs and sources
  ("—SOUTHEY.", "Lardner's Cabinet Cyclopedia."), footnotes, editor's notes
  ("[Such is the history of Ferguson's struggles…]", "I regret exceedingly that
  the Tale of Lady Jean…—W. C."), "To be continued".
- Several pieces join with " | ". Keep `series` and `subsections` as they are.

Front/back matter must be recovered wherever YOLO put it:
- in its own box read as text (penny p19 b9, p25 b2; Chambers p20 b26–27);
- boxed as a title (penny p6 b3, p25 b4/b8; Saturday p15 b8; Chambers p2
  b4–5, p17 b2/b11, p19 b5);
- merged into the first or last paragraph box (Saturday p10 b9, Chambers p11
  b6, p4 b6);
- set aside as furniture: asterisked footnotes, "[To be continued.]" (penny
  p17; Saturday p14, p18, p22).

**Evidence.** About 50 of the 63 `role` errors. Owen's notes flag several
sources as extremely important (Library of Entertaining Knowledge, Library of
Useful Knowledge, Working Man's Companion, the Lady Jean note).

**Status:** decided.

## 2. Sign-off (inline source) detection

**Decision.**
- Keep the main rule: a dash then a short source phrase.
- No-dash fallback (Owen): keep the 2–8 word check and the capitalisation
  check. Widen the lowercase exceptions to the prepositions and conjunctions
  titles leave lowercase (from, by, with, upon, into, through, among, over,
  under, against, after, before, near, or, nor, but, as, plus of, the, and,
  in, on, at, for, to, a, an). Drop the "looks like a citation" check
  (possessive / source word last), which only suits one kind of source. Add
  "Bible" to the source words.
- Separate **recording** a source from **ending** an article:
  - record any short final phrase of an article's last paragraph as back
    matter (a false positive only mislabels a phrase);
  - end an article only on a dash, italics, or a boundary confirmed otherwise
    (a title or masthead follows).
- Accept long source blocks ("Murray's Literary History of Galloway. Second
  Edition. (To be continued.)"; "Gazetteer of Scotland, Thomas Ireland, Jun.,
  Edinburgh, 1832").
- Recover italics: re-run Document AI OCR with style info (per-word italic),
  after checking the cost per page. A reader knows a source by its dash,
  italics and position; OCR often drops the dash.
- Inline sign-offs already detected are cut out of the body text into
  `back_matter`.

**Evidence.** Missed with the dash dropped by OCR: "Elliot's Letters from the
North of Europe" ("from"), "History of the Bible" (Chambers p8 b8, b17); no dash
or possessive: "Tour of a German Prince." (penny p26). Sources that must still
be caught: "Library of Entertaining Knowledge" (Chambers p13 b13), "Paradise
Lost"-type titles.

**Status:** decided. (An LLM check for ambiguous endings was considered and
not chosen.)

## 3. Series and continuations (general rules)

**Decision.** Two independent fields; a piece can have both (Archery).

- **Series** (`series`): a recurring feature where each piece has its own
  subject. Rule: two stacked headings where the first (the *leader*) recurs
  across issues: leader = series, second = title ("BIOGRAPHIC SKETCHES." +
  "DR. ALEXANDER MURRAY."). Also: a title that recurs on its own is a series
  ("THE WEEK"), and numbered titles are series parts ("FAMILIAR REMARKS ON
  ARCHITECTURE. I."). A leader seen in only one issue so far is a candidate
  until it recurs. Series headings caught inside figure boxes count too
  ("BRITISH ANIMALS." over the Mole).
- **Continuation** (`continues_article_id`): one piece carried across issues.
  Rule: continuation language. "To be continued", "To be concluded in our
  next" and "(To be continued.)" close a part; "Concluded from No. I.",
  "Continued.", "[Concluded from our last.]" open one. Parts are joined by
  title, or by leader plus title for series pieces.
- Continuation notes are front/back matter, not title text.

**Agreed so far.** Series: British Animals, Familiar Remarks on Architecture,
Botanical Diversions (tentative), The Week, Biographic Sketches, Column for the
Boys, the Committee of General Literature and Education's notices.
Continuations: Van Diemen's Land, Jagganátha, Lady Jean, Emigration (Chambers),
Formation of Scottish Society, Archery, Sketches in Topography, Origin and
Progress of Printing (likely).

**Evidence.** Series headings joined into titles: penny p12 b1, p20 b4;
Saturday p9 b1; Chambers p5 b13, p12 b6, p15 b1, p21 b10, p23 b1–2.

**Status:** decided.

## 4. Filler items (unmarked short items)

**Decision.** Find item boundaries with no title or run-in head from two
signals, not an LLM (Owen: an LLM check would be costly and vague):
1. **Printed rules:** detect the short horizontal lines printed between items
   directly from the page image (YOLO doesn't box them).
2. **The volume index:** OCR each volume's index into entries with printed
   page numbers; a page with fewer items than index entries flags a missed
   boundary.

Fillers are not only at issue ends, and some run to several paragraphs, so
"each paragraph box is its own item" is not used.

**Evidence.** 16 of 22 merges are penny fillers: p8 (9 items run together;
some have a head, some a rule above, some nothing, e.g. b11), p11 b8, p16
b8–10, p20 b2, p26 b5 and b8 (the ghost story is 7 boxes long).

**Status:** decided. Needs the index pages OCR'd and parsed (penny vol. 1
index PDF supplied).

## 5. Run-in heads and subsections

**Decision.**
- Run-in heads missed so far: in capitals ending "?" ("WHICH WAS THE GREATER
  FOOL?", Saturday p23 b2); heads with lowercase words ("Science preceding
  Art.—", "The Secret of great Workers.—", penny p8, p11); heads scrambled by
  tilt at a box start ("VEGETABLES.—", Chambers p24 b4); "VATICAN.—" (Chambers
  p22 b11).
- A capitals run-in head with its own source at the end is an item, not a
  subsection ("NEGRO DOCTOR" with "—Edinburgh Cabinet Library", Chambers p14
  b22).
- Record all subsection heads, including one-word mixed-case ones (Archery:
  Butts, Targets, Position, Roving, Flight-Shooting; "Arrows." after OCR runs
  it together).
- An in-line title run into a poem's text is a title ("WHAT is true
  knowledge?", Saturday p11 b8).

**Status:** decided.

## 6. Captions, figures and tables

**Decision.**
- A caption or title inside a figure box is recovered as caption / title
  (penny p9 b1, Saturday p4 b1).
- A "caption" that introduces a table is text (Saturday p21 b9).
- An illustration that precedes its article's title on the page belongs to
  that article (Saturday p12 b1).
- Table boxes get a `table` role (jumbled numbers; leave out of topic
  modelling and WER). Table-structure OCR or transcription only where the
  argument needs a table.

**Status:** decided.

## 7. Imprint and editorial notices

**Decision.**
- Imprint matches only publisher lines (LONDON:, JOHN WILLIAM PARKER, Sold by…,
  Printed by…); stop treating the rest of the page as imprint after a title.
- The Committee of General Literature and Education's notices are articles
  (series; `article_type = editorial_notice`). Publisher announcements and
  advertising stay imprint.
- Errata and notices to readers are kept as articles (possible `article_type`
  label).

**Evidence.** Saturday p16 b15–16, p24 b18–19 (notices lost as imprint);
p24 b20–23 (announcement, correctly imprint); p16 b14 (Erratum kept).

**Status:** decided.

## 8. Text recovery and junk boxes

**Decision.**
- Side-edge fragments (line-end words just past a box's side, often from
  page tilt) rejoin their lines in that box, instead of becoming strip boxes.
- Single unboxed lines inside the content area are recovered too ("4585
  tons.", Chambers p21 b8).
- Junk boxes and the HathiTrust watermark are furniture, not text (Saturday
  p11 b1, p19 b2; Chambers p20 b17).
- Printer's marks inside text boxes are removed ("VOL. I.", "3-2", "02").
- Stray "44" / "66" before an opening word is an OCR'd quotation mark.

**Evidence.** 8 misplacements (Chambers pp. 7, 18, 20, 24), 1 missed.

**Status:** decided.

## 9. Duplicate scan pages

**Decision.** Detect pages whose printed number repeats within an issue and
whose text matches; skip them and record `duplicate_of`. Article numbers after
the duplicates will shift.

**Evidence.** Penny PDF pp. 22–23 repeat printed pp. 20–21 (also in the
HathiTrust PDF); excluded from the evaluation.

**Status:** decided.

## 10. Metadata (built during v1, kept)

Issue numbers without punctuation; the sequence check (`issue_check`) with
OCR-confusable digit correction and new-series flags; full issue dates on
every page; raw `masthead_text`. No metadata errors in the evaluation.

**Status:** built (in v1).
