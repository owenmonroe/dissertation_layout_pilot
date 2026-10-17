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

**Status:** built 2026-10-16.
- Articles have `front_matter` / `back_matter` (pieces joined with " | ").
  Whole boxes get the roles `front_matter` / `back_matter`.
- Text cut from a box is recorded in the regions table's `front_text` /
  `back_text` columns and left out of the article text.
- Of the 41 logged front/back-matter errors, 37 are fixed. Still open:
  - the Lady Jean ballad epigraph merged into the first paragraph (Chambers
    p4 b6);
  - the long editor's introduction and dateline before the Emigration letter
    (Chambers p20 b26–27);
  - a footnote scrambled by page tilt (Chambers p18 b11; see decision 8).
- One correction found along the way: an illustration above a title moves to
  that article only if it heads the page, or carries its own printed heading
  ("BRITISH ANIMALS."). A figure after an article's own title or text stays
  with that article.

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

**Status:** built 2026-10-16, except italics. (An LLM check for ambiguous
endings was considered and not chosen.)

The rules as built:
- **Dash sign-off.** A dash, then 2–8 words in title case. The phrase may not
  end on a small word or a comma ("- Astronomy, as" is the start of a
  sentence). It is cut into `back_matter` and ends the article.
- **No-dash final phrase.** Recorded as back matter but doesn't end the
  article. It is skipped when the word before it is capitalised, which means
  an OCR full stop inside a name ("…the Roya. Academy of Arts.").
- **Short source boxes** after the text are back matter ("B. MONTAGU'S
  Selections.", "D. C. July, 1832.").

Checked against the log:
- every v1-correct row that changed is an improvement (a source now recorded);
- article boundaries are unchanged apart from the Saturday p12 fix;
- the 5 verified pages still pass.

Still to do: italics (re-run Document AI with style info after checking the
cost).

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

**Status:** built 2026-10-16 (`series.py`).
- New article columns: `series`, `series_part`, `series_evidence`,
  `continues_article_id`, `continued_by_article_id`, `continuation_evidence`.
  The `*_evidence` columns say which rule fired, for checking.
- Series heading boxes get the role `series_heading`.
- **Series found:**
  - British Animals: Dormouse, Mole;
  - The Week: issues 1–3;
  - Biographic Sketches: Dr. Adam, James Ferguson, Dr. Alexander Murray;
  - Column for the Boys: Archery, both parts;
  - Familiar Remarks on Architecture: part I;
  - Botanical Diversions: marked candidate, since it appears in one issue
    only.
- **Continuations linked:**
  - Van Diemen's Land;
  - Jagganátha (by the shared word, plus "in our first number");
  - Lady Jean;
  - Formation of Scottish Society;
  - Emigration, issues 1→2→3;
  - Archery. Its p15 part, printed under "COLUMN FOR THE BOYS." alone, takes
    the title Archery from its continuation.
- **New:** "To be continued" at the end of a paragraph box is now back matter
  (with the source before it) and ends the part. This also fixed the
  "American Musquitoes!" merge (Chambers p20 b24).
- **Not done:**
  - The Swallow (penny p12) has no heading of its own; it is printed under
    the Dormouse's "BRITISH ANIMALS." heading. No general rule finds it: "the
    next piece on the page inherits the series" would wrongly put nine other
    pieces into series. A hand correction was tried and then removed (Owen:
    no hand-entered facts; the volume index lists the Swallow under British
    Animals and is the route for cases like this). Known miss;
  - the Committee notices wait for decision 7;
  - Origin and Progress of Printing and Sketches in Topography have only one
    part in the sample, so nothing to link yet.

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

**Status:** built 2026-10-16 (`rules.py`, `volume_index.py`).

**1. Printed rules** (`rules.py`). How rules are found:
- A rule is a solid, isolated horizontal line in the page image.
- Detections on neighbouring rows are grouped, so a tilted rule counts once.
- It must be centred in its column on the page grid.

Rules ignored:
- off-centre lines: table totals, footnote rules;
- lines inside illustrations;
- lines under titles (Chambers' title underlines), captions and figures;
- lines in or under boxes of figures (tables).

What a rule does:
- A rule between two text boxes starts a new item.
- A rule running through a YOLO text box splits the box (new region type
  `rule_split`).
- A footnote under its rule is back matter.

Results:
- 16 of the 22 logged merges are fixed: penny p8 ×5, p11, p16 ×3, p20, p26
  ×2; Saturday p23; Chambers p14, p16, p20.
- No v1-correct boundary was broken, except Saturday p21 b10. There the
  bell-weights table sits under a real printed rule and is now its own item
  (Owen to decide).
- Still merged (no rule printed):
  - penny p8 b3–5, three italic run-in heads with lowercase words
    (decision 5);
  - penny p8 b11, Michael Angelo, at a column top;
  - Chambers p22 VATICAN and p24 VEGETABLES (decisions 5 and 8);
  - Willie Cossar Pins (Chambers p16): its rule is only half detected, and
    it is a run-in head mid-box.

**2. Volume index** (`volume_index.py`; the PDF is in
`build_texts/volume_index/`, set per magazine as `volume_index` in
`magazine_rules_config.py`; penny only so far).
- Entries are parsed from the PDF text layer (three columns, hanging indent).
- Each entry is matched by its distinctive words to the articles on the
  printed pages it cites.
- Output: `<mag>_index_check.csv`, one row per entry: matched / shared /
  unmatched.
- Each article gets an `index_entries` column: subject terms, and the only
  heading untitled fillers have ("Air-balloon", "Ghost Story by Judge
  Powell").
- The index flags pages; it doesn't change the articles.
- On penny, "shared" points at the remaining p8 merges ("Instruction and
  Amusement", "Secret of great Workers" and "Devotion of great Minds" all
  match "A Popular Error"; "Angelo" and "Chinese" share one article).
- "Unmatched" is mostly garbled index OCR ("Dorse" for Dormouse).

Possible later uses:
- the index groups series pieces ("British animals, the Dormouse, 12; the
  Swallow, ib.; the Mole, 20"), which could replace the Swallow's manual
  series correction;
- Saturday and Chambers need their volume indexes.

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

**Status:** built 2026-10-16. Owen: rules must generalise to many more, and
more complex, volumes; it's fine to miss some articles, as long as the rules
aren't brittle. So each rule rests on a printing convention, not on
particular pages:
- "?" and "!" end a run-in head, but only for heads in capitals ("WHICH WAS
  THE GREATER FOOL?"). In mixed case they usually end speech ("Then-oh
  William!").
- With a dash after it, a head may have lowercase words: it begins and ends
  capitalised, with at least half its main words capitalised ("Science
  preceding Art.—", "The Secret of great Workers.—"). Without a dash, heads
  stay strict.
- A spaced dash after a one-word capitals head counts ("VATICAN -Perhaps").
- No run-in head in a table (a box mostly of figures).
- After a paragraph ending in a colon ("…as under :-", "…of our own day:—"),
  the next box continues the item. A head there is at most a subsection.
- A capitals head whose paragraph ends with its own dash sign-off is an item,
  not a subsection.

Fixed:
- penny p8 b4 (Secret of great Workers) and p11 (Science preceding Art);
- Saturday p23 (titled "WHICH WAS THE GREATER FOOL?");
- Chambers p22 VATICAN;
- also, from the colon rule: penny p15 TO A DAISY stays inside Poesie, and
  penny p18 "Under Seven" (a table row) is no longer a head.

Not fixed (would need italics, or page-specific rules):
- penny p8 b3 "Instruction and Amusement" (no punctuation) and b5 "Devotion
  of a great Mind to its Duties" (OCR lost the dash);
- Saturday p11 "WHAT is true knowledge?" (a mixed-case title in a poem);
- Chambers p24 VEGETABLES (tilt; decision 8).

A mid-box head rule was considered and dropped: the cases thought to need it
turned out to be at box starts.

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

**Status:** built 2026-10-16.
- **Captions inside illustration boxes.** Bracketed text inside a figure box
  becomes the figure's caption ("[Restored View of Pompeii.]",
  "[Date-Palm, and Fruit.]"). A capitals heading inside a figure box was
  already used as the title (Pompeii, Jagganátha) or the series heading
  (British Animals).
- **YOLO captions read as text.** A "caption" that ends in a colon
  (introducing what follows), or that has no illustration on its page, is
  text. Saturday p21's "The following are the weights of the principal bells
  in Europe:—" now opens an item with the bell table. That item is separate
  from History of Bells because of the printed rule above it. Owen confirmed:
  keep it separate, with its intro.
- **Tables.** A box gets the role `table` if YOLO typed it as a table, or if
  it is mostly figures (30% or more of words) with hardly any running prose,
  so a paragraph about numbers stays text (Saturday p6, Figure 9).
  - Tables stay with their article but are left out of its text (Owen: keep
    them labelled and out of topic modelling and WER). New article columns
    `n_tables` and `table_text`.
  - A capitals opening after an item that is only a table starts a new item.
  - Found: penny p7 (religions), p18 (passage prices); Saturday p6
    (population), p16 (bread), p21 (bells), p22 (mortality); Chambers p16
    (libraries).
- **Illustration above its title:** built with decision 1.
- Subsections (Owen): the least important element. No rules only for
  recording them; it's fine if they stay article text.

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

**Status:** built 2026-10-16.
- **Imprint matches publisher lines only.** The Committee was taken out of
  Saturday's imprint pattern. After the imprint starts, a heading that isn't
  itself a publisher line makes the page articles again.
- **Publisher's announcements are imprint.** Selling wording in a box's first
  line ("ready for delivery", "price Sixpence", "monthly parts", "sold by"),
  or a heading followed by such a box, low on an issue's last page (Saturday
  p24 b20–23).
  - Limited to the last page because ordinary prose has phrases like "to be
    had at the low price" (Chambers p10).
- **New article column `article_type`:** `article` or `editorial_notice`.
  - A notice is recognised by shared title wording: a title that is just
    "NOTICE", "ERRATUM" or "TO CORRESPONDENTS" (or "NOTICE TO …").
  - "Notice of …" is the period's wording for a biography, so it doesn't
    count.
  - Addresses and introductions to readers ("Reading for All", "The Editor's
    Address to his Readers", "A Postscript to our First Readers") are normal
    articles (Owen).
  - Plus each magazine's own publishing body (`editorial` in
    `magazine_rules_config.py`; Saturday: the Committee of General Literature
    and Education).
- **Found:** the Committee's notices (Saturday p16, p24), with series "The
  Committee of General Literature and Education" from the recurring-title
  rule; Saturday's Erratum.
- **Imprints kept per issue,** for publishing history (Owen).
  - Low on an issue's last page, a box YOLO set aside or called a figure is
    imprint if it has imprint wording (penny's "LONDON:—CHARLES KNIGHT …" on
    all three issues; Chambers p8; Saturday's "C. RICHARDS, Printer").
  - New table `<mag>_imprints.csv` (also in SQLite): one row per issue, with
    number, date, page and the full imprint text in reading order.
  - Already visible in the sample:
    - penny's printer, William Clowes, moves from Duke Street, Lambeth to
      Stamford Street (issue 3);
    - Chambers' London publication changes from "for R. & J. CHAMBERS" to
      "by W. S. ORR" (issue 3);
    - Saturday's prices and agents.

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

**Status:** built 2026-10-16 (`text.py`). Nearly all of these came from one
step, the recovery of OCR lines YOLO didn't box, which turned tilt strips,
junk and the watermark into boxes.
- **Watermark.** The scan's stamps ("hdl.handle.net", "Google-digitized",
  "Original from", "Digitized by", "… GMT") are never text.
- **Tilt strips.** A recovered block averaging 1.5 words a line or fewer is a
  strip of cut-off words, not a paragraph. On the development pages, real
  recovered paragraphs run 2.5–9.6 words a line and strips exactly 1.0.
  - If the strip is narrow and lies at a text box's side edge, each word
    rejoins the box line at its height (end or start of the line).
  - Otherwise it is junk and is set aside as unboxed text ("10 кат his this
    rith hat", "Is an").
- **Single lines.** A leftover line at a box's side edge rejoins its line;
  one just above or below a box in its column becomes the box's first or
  last line ("4585 tons.", Chambers p21).
  - Nothing is rejoined in the top 15% of the page, where masthead lines are
    read for the issue number. Issue numbers are unchanged.
- **Printer's marks** are removed from text boxes:
  - a signature after the last sentence ("… sea. C", "… crime. 3");
  - "VOL. I." at a box's end;
  - "02" at a box's start before a lowercase word.
- **OCR'd quotation marks:** "44"/"66" before a capitalised word becomes an
  opening quotation mark ("44 When he was …" → "“When he was …").
- **Result:**
  - all 8 logged misplacements fixed (no strip boxes remain);
  - the missed line, both junk boxes and the watermark fixed;
  - printer's marks fixed on penny p1, p9, p17, Saturday p1, p17 and
    Chambers p12, p13.
  - The only boxes still built from unboxed lines are real ones: Saturday's
    agents list (imprint), a masthead fragment and the Chambers p18
    footnote.
- **Not fixed:**
  - "… their own 3-2" (Saturday p19): a signature after a word, not a full
    stop. Removing number ranges there would risk real text ("pp. 3-4").
  - VEGETABLES (Chambers p24): its head is scrambled into the line before by
    tilt.

## 9. Duplicate scan pages

**Decision.** Detect pages whose printed number repeats within an issue and
whose text matches; skip them and record `duplicate_of`. Article numbers after
the duplicates will shift.

**Evidence.** Penny PDF pp. 22–23 repeat printed pp. 20–21 (also in the
HathiTrust PDF); excluded from the evaluation.

**Status:** built 2026-10-16 (`duplicates.py`).
- **The rule is text, not the printed number,** which OCR often misreads. A
  page is a duplicate when it shares 60% or more of its words with one of
  the six pages scanned before it.
- **Measured on the development pages:** the two duplicates overlap their
  originals by 0.97 and 1.00. Every other page overlaps its predecessors by
  0.19 at most, so the threshold has a wide margin.
- **Duplicates are left out of article extraction.** The pages table records
  `duplicate_of`, and their boxes stay in the regions table with role
  `duplicate_page`.
- **Result:**
  - penny scan pages 22–23 are found (duplicates of 20–21);
  - none are found in Saturday or Chambers;
  - The Library now runs from printed p21 to p24 without a copy in between;
  - penny has 53 articles (was 58).

## 10. Metadata (built during v1, kept)

Issue numbers without punctuation; the sequence check (`issue_check`) with
OCR-confusable digit correction and new-series flags; full issue dates on
every page; raw `masthead_text`. No metadata errors in the evaluation.

**Status:** built (in v1).
