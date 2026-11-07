"""Series and continuations (v2, decision 3): two independent fields, and a
piece can have both (Archery is a part of "Column for the Boys" and continues
the previous issue's Archery).

  - series: a recurring feature where each piece has its own subject.
      - two stacked headings where the first (the leader) recurs across
        issues: leader = series, second = title ("BIOGRAPHIC SKETCHES." +
        "DR. ALEXANDER MURRAY."). A leader can also be printed inside an
        illustration box above the title ("BRITISH ANIMALS." over the Mole),
        or run into one title box, seen in two issues over different subjects
        ("NATIONAL GALLERIES FOR THE FINE ARTS AT MUNICH. THE GLYPTOTHEK.");
      - a leader seen in one issue only is a candidate (series_evidence says
        so) until it recurs;
      - a title that recurs on its own in different issues, with no
        continuation language between them, is a series ("THE WEEK");
      - a number on the series heading is the series' own numbering ("THE
        NATURAL HISTORY OF THE MONTHS. I. JANUARY.": series_part I), and so is
        one opening the title under a leader ("A DISCOURSE ON GEOLOGY." / "I.
        NATURE OF GEOLOGY."): number and subject change from piece to piece.
  - continuation (continues_article_id): one piece carried across issues,
    with the same title apart from a part number or a note (Owen, v3 decision
    8). A numbered title is a part of one piece, not a series: "ON GARDEN
    HERBS. I." (part, new in v3). Part 1 implies more to come, even if nothing
    is printed; a later part implies an earlier one, even if it wasn't run.
    A part is closed by "To be continued" / "To be concluded" (back matter)
    and opened by "Continued.", "Concluded from No. I.", "[Concluded from
    our last.]" (front matter) or "in our first number" near the start of
    the text. Parts are joined by title (or by series plus title), when at
    least one side has continuation language. An opening part with no title
    match joins the latest unfinished part that shares a distinctive title
    word ("JAGGANATHA"). A series piece printed under the leader alone
    takes its title from its continuation ("COLUMN FOR THE BOYS." → Archery).

Recurrence is counted within the pages run together (one volume's sample).
"""

import re

from articles import SMALL_WORDS, TITLE_SMALL_WORDS, Article

FIGURE_LEADER = re.compile(r"^\s*([A-Z][A-Z'’&-]+(?: [A-Z][A-Z'’&-]+){1,5})\b")  # "BRITISH ANIMALS."
# A title with a part number: "ON GARDEN HERBS. I.", "KNIGHTS OF MALTA.—No. III.",
# not "BY FRANCIS I." (no stop or dash before the number).
PART = re.compile(r"^(.*?\S)\s*[.:]\s*[—–-]{0,2}\s*(?:No\.?\s*|Part\s+)?([IVXLC]{1,6}|\d{1,3})\.?$", re.I)
PART_DASH = re.compile(r"^(.*?\S)\s*[—–-]{1,2}\s*(?:No\.?\s*|Part\s+)([IVXLC]{1,6}|\d{1,3})\.?$", re.I)
# A number on a series heading: "THE NATURAL HISTORY OF THE MONTHS. I. JANUARY."
SERIES_NUMBER = re.compile(r"^(.+?)\.\s+([IVXLC]{1,6})\.\s+(\S.*)$")
# Under a leader: "I. NATURE OF GEOLOGY." Only I, V, X: "M. TURGOT." is a name.
LEADING_NUMBER = re.compile(r"^([IVX]{1,5})\.\s+(\S.*)$")
# "No. V." opening the title under a leader, with the piece's own subject
# ("No. V. LITTLE MUSGRAVE..."): the series' number (v4, rule 3). The title
# keeps it, as printed.
NO_NUMBER = re.compile(r"^No\.?\s*([IVXLC]{1,6}|\d{1,3})\.?,?\s+\S", re.I)
# A leader printed with its number ("ON WILLS. No. IV" / "WILLS OF PERSONAL
# PROPERTY CONTINUED."), or name, number and subject on one line ("PUBLIC
# IMPROVEMENTS. —No. II., PROVINCIAL TOWNS."): the name is the series, and
# the title is the whole heading, since the number is printed with the name.
NAMED_NUMBER = re.compile(r"^(.*?[A-Za-z].*?)\s*[.,]?\s*[—–-]{0,2}\s*No\.?\s*([IVXLC]{1,6}|\d{1,3})\b\.?,?\s*(.*)$", re.I)
PART_THE = re.compile(r"\bpart\s+the\s+(second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\b", re.I)
ORDINAL_NOTE = re.compile(r"\b(second|third|fourth|fifth|sixth|seventh|eighth|ninth|tenth)\s+(?:article|paper|part)\b", re.I)
ORDINALS = {"second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
            "eighth": 8, "ninth": 9, "tenth": 10}
OPENS = re.compile(r"\b(?:continued|concluded)\b", re.I)
OPENS_TEXT = re.compile(r"\bin our (?:first|last|former|previous|preceding) (?:number|no\b)", re.I)
OPENS_TEXT_CHARS = 300
CLOSES = re.compile(r"\bto be (?:continued|concluded)\b", re.I)
RUN_IN_LEADER_WORDS = 2  # at least: "DR. ADAM." and "M. TURGOT." are names
DISTINCTIVE_LEN = 6  # letters in a title word shared by two parts with different titles


def key(text: str) -> str:
    """Content words, for matching headings printed differently
    ("ON THE FORMATION OF SCOTTISH SOCIETY" / "FORMATION OF SCOTTISH SOCIETY",
    "COLUMN FOR THE BOYS." / "Column for the Boys")."""
    words = re.findall(r"[A-Za-z]+", text.upper())
    return " ".join(w for w in words if w.lower() not in TITLE_SMALL_WORDS)


def display(text: str) -> str:
    """One spelling of a series name for every piece: "Column for the Boys".
    A word broken across lines is joined: "EXPERI- MENTAL" → "Experimental"."""
    text = re.sub(r"(?<=[A-Za-z])-\s+(?=[A-Za-z])", "", text)
    words = re.findall(r"[A-Za-z'’]+", text)
    return " ".join(w.capitalize() if i == 0 or w.lower() not in SMALL_WORDS else w.lower()
                    for i, w in enumerate(words))


def clean(text: str) -> str:
    return text.strip().rstrip(".").strip()


def figure_leader(a: Article) -> str | None:
    """A heading printed inside an illustration box above the title."""
    if not a.title_regions:
        return None
    first = a.title_regions[0]
    for f in a.figures:
        if f.page == first.page and f.order < first.order:
            m = FIGURE_LEADER.match(f.text or "")
            if m:
                return m.group(1)
    return None


def caption_leader(a: Article) -> str | None:
    """A numbered heading printed with the illustration before the title, as
    its caption: "A BRIEF HISTORY OF THE FINE ARTS. VIII." over the picture, then
    "THE HISTORY OF COPPER-PLATE ENGRAVING." (v5). It stays the caption too. A
    caption with no number ("HEREFORD CATHEDRAL.") is only a caption."""
    if not a.title_regions:
        return None
    first = a.title_regions[0]
    for c in a.captions:
        before = c.page < first.page or (c.page == first.page and (c.order or 0) < (first.order or 0))
        if before and c.text.isupper() and PART.match(c.text.strip()):
            return c.text.strip()
    return None


def leader_of(a: Article):
    """(leader, rest of the title, where the leader was printed)."""
    parts = [r.text for r in a.title_regions]
    # A heading line with no YOLO box, under one with no full stop, is the
    # title running on ("ENGLISH INGENUITY AND ENTERPRISE" / "IN A NEW POINT OF VIEW."):
    wraps = a.title_regions and a.title_regions[-1].yolo_type == "unboxed_ocr" \
        and not parts[0].rstrip().endswith(".")
    if len(parts) >= 2 and not wraps:
        return clean(parts[0]), clean(" ".join(parts[1:])), "stacked headings"
    leader = figure_leader(a)
    if leader:
        return clean(leader), a.title, "heading in illustration box"
    leader = caption_leader(a)
    if leader:
        return clean(leader), a.title, "numbered caption over the illustration"
    return None


def roman(text: str) -> int:
    if text.isdigit():
        return int(text)
    values = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100}
    total, prev = 0, 0
    for c in reversed(text.upper()):
        v = values[c]
        total, prev = total - v if v < prev else total + v, max(prev, v)
    return total


def base_title(a: Article) -> str:
    """The title without its part number: parts of one piece share it."""
    m = PART_DASH.match(a.title) or PART.match(a.title)
    return m.group(1) if m and a.part else a.title


def opens_part(a: Article) -> bool:
    return bool(OPENS.search(a.front_matter) or OPENS_TEXT.search(a.text[:OPENS_TEXT_CHARS])) \
        or (bool(a.part) and roman(a.part) >= 2)


def closes_part(a: Article) -> bool:
    return bool(CLOSES.search(a.back_matter)) or (bool(a.part) and roman(a.part) == 1)


def run_in_leaders(articles: list[Article], leaders: dict) -> set:
    """Openings of one-box titles printed in two issues over different
    subjects. A numbered title stays a part of one piece ("ON GARDEN HERBS. I.")."""
    seen = {}  # opening -> (issues, subjects)
    for a in articles:
        head, dot, rest = a.title.partition(". ")
        if leaders[a.article_id] or not dot or not rest.strip() \
                or len(head.split()) < RUN_IN_LEADER_WORDS or PART.match(clean(a.title)):
            continue
        issues, subjects = seen.setdefault(key(head), (set(), set()))
        issues.add(a.issue_seq)
        subjects.add(key(rest))
    return {k for k, (issues, subjects) in seen.items() if len(issues) >= 2 and len(subjects) >= 2}


def numbered_leader(found):
    """(name, number, whole heading) when the leader carries its number."""
    leader, rest, where = found
    m = NAMED_NUMBER.match(leader)
    if m and not m.group(3).strip() and len(m.group(1).split()) >= 1:
        return clean(m.group(1)), m.group(2).upper(), f"{leader} {rest}".strip()
    if where == "numbered caption over the illustration" and (p := PART.match(leader + ".")):
        return clean(p.group(1)), p.group(2).upper(), rest  # the title stays the article's own
    return None


def assign_series_leaders(articles: list[Article]) -> None:
    """Split leaders off titles, before the titles are tidied."""
    leaders = {a.article_id: leader_of(a) for a in articles}
    numbered = {}
    for a in articles:
        found = leaders[a.article_id]
        if found and numbered_leader(found):
            name, number, whole = numbered_leader(found)
            numbered[a.article_id] = (number, whole)
            leaders[a.article_id] = (name, found[1], found[2])
    issues = {}  # leader key -> issues it was printed in, as a leader or a whole title
    for a in articles:
        found = leaders[a.article_id]
        heading = found[0] if found else a.title
        if heading:
            issues.setdefault(key(heading), set()).add(a.issue_seq)
    recurring = {k for k, seen in issues.items() if len(seen) >= 2}
    leader_keys = {key(f[0]) for f in leaders.values() if f}
    run_in = run_in_leaders(articles, leaders)

    for a in articles:
        found = leaders[a.article_id]
        if found:
            leader, rest, where = found
            seen = sorted(issues[key(leader)])
            a.series = display(leader)
            a.title = rest
            number = LEADING_NUMBER.match(rest)
            if number:
                a.series_part, a.title = number.group(1), number.group(2)
            elif NO_NUMBER.match(rest):
                a.series_part = NO_NUMBER.match(rest).group(1).upper()
            if a.article_id in numbered:
                a.series_part, a.title = numbered[a.article_id]
            a.series_evidence = (f"leader recurs (issues {', '.join(map(str, seen))}); {where}"
                                 if key(leader) in recurring
                                 else f"candidate: leader in one issue so far; {where}")
            if where == "stacked headings":
                a.title_regions[0].role = "series_heading"
        elif a.title and key(a.title) in recurring and key(a.title) in leader_keys:
            # The leader printed alone ("COLUMN FOR THE BOYS."): its title may
            # come from a continuation (link_continuations).
            seen = sorted(issues[key(a.title)])
            a.series = display(a.title)
            a.series_evidence = f"leader recurs (issues {', '.join(map(str, seen))}); printed alone"
            for r in a.title_regions:
                r.role = "series_heading"
            caption_title(a)
        else:
            # A known leader run into one title box: "BIOGRAPHIC SKETCHES. DR. ADAM."
            head, dot, rest = a.title.partition(". ")
            named = NAMED_NUMBER.match(clean(a.title)) if a.title else None
            if dot and rest and (key(head) in run_in or (key(head) in recurring and key(head) in leader_keys)):
                a.series, a.title = display(head), rest
                a.series_evidence = "leader recurs; run into the title box"
            elif named and named.group(3).strip() and len(named.group(1).split()) >= 2:
                # Name, number and its own subject in one heading (rule 3)
                a.series, a.series_part = display(named.group(1)), named.group(2).upper()
                a.series_evidence = "series name, number and subject in one heading"


def caption_title(a: Article) -> None:
    """Under a recurring leader, an all-capitals caption below the heading is
    the piece's title ("BRITISH ANIMALS." / cut / "THE DORMOUSE.")."""
    r = a.caption_heading
    if r is not None:
        a.title = clean(r.text)
        r.role, r.note = "title", "caption under a recurring series heading: the title"
        if r in a.captions:
            a.captions.remove(r)
        a.title_regions.append(r)


def read_parts(articles: list[Article]) -> None:
    """Part numbers: from the title ("ON GARDEN HERBS. I."), or a note in the
    front matter ("Second Article."); a number on a series heading is the
    series' own."""
    for a in articles:
        m = SERIES_NUMBER.match(a.title)
        if m and not a.series and len(m.group(1).split()) >= 2:
            a.series, a.series_part, a.title = display(m.group(1)), m.group(2), m.group(3)
            a.title = clean(a.title)
            a.series_evidence = "numbered series heading run into the title box"
            continue
        m = PART_DASH.match(a.title) or PART.match(a.title)
        if m and len(m.group(1).split()) >= 2:
            a.part = m.group(2).upper()
            continue
        m = ORDINAL_NOTE.search(a.front_matter) or PART_THE.search(a.front_matter)
        if m:
            a.part = str(ORDINALS[m.group(1).lower()])


def link_continuations(articles: list[Article]) -> None:
    def match(earlier: Article, later: Article) -> str | None:
        if earlier.issue_seq >= later.issue_seq or earlier.continued_by_article_id:
            return None
        language = closes_part(earlier) or opens_part(later)
        if not language:
            return None
        if earlier.series or later.series:
            if key(earlier.series) != key(later.series):
                return None
            if key(base_title(earlier)) == key(base_title(later)) or key(earlier.title) == key(earlier.series):
                return "same series and title" if key(base_title(earlier)) == key(base_title(later)) \
                    else "same series; earlier part printed under the leader alone"
            return None
        if key(base_title(earlier)) and key(base_title(earlier)) == key(base_title(later)):
            return "same title"
        return None

    for later in articles:
        candidates = [a for a in articles if a is not later]
        for earlier in reversed(candidates):  # the most recent earlier part first
            how = match(earlier, later)
            if how:
                link(earlier, later, how)
                break
        else:
            if opens_part(later) and not later.continues_article_id:
                words = {w for w in key(later.title).split() if len(w) >= DISTINCTIVE_LEN}
                for earlier in reversed(articles):
                    if earlier.issue_seq < later.issue_seq and closes_part(earlier) \
                            and not earlier.continued_by_article_id \
                            and words & set(key(earlier.title).split()):
                        link(earlier, later, "continuation language; shared title word")
                        break


def mark_continuations(articles: list[Article]) -> None:
    """Record what the page says or implies, whether or not the other part
    was run: "continued from" needs no link (Owen, v3 decision 8)."""
    for a in articles:
        a.continued_from = bool(a.continues_article_id) or opens_part(a)
        a.to_be_continued = bool(a.continued_by_article_id) or closes_part(a)


def link(earlier: Article, later: Article, how: str) -> None:
    later.continues_article_id = earlier.article_id
    earlier.continued_by_article_id = later.article_id
    signs = [s for s, ok in (("'to be continued' closes the earlier part", closes_part(earlier)),
                             ("continuation note opens this part", opens_part(later))) if ok]
    later.continuation_evidence = f"{how}; {'; '.join(signs)}"
    if earlier.series and key(earlier.title) == key(earlier.series) \
            and key(later.title) != key(later.series):
        earlier.title = later.title  # "COLUMN FOR THE BOYS." → "ARCHERY"
        earlier.series_evidence += f"; title from its continuation ({later.article_id})"


def series_of_recurring_titles(articles: list[Article]) -> None:
    """A title printed on its own in several issues, not linked as one piece
    carried on, is a recurring feature: "THE WEEK"."""
    linked = {a.article_id for a in articles
              if a.continues_article_id or a.continued_by_article_id or a.part}
    issues = {}
    for a in articles:
        if a.title and not a.series and a.article_id not in linked:
            issues.setdefault(key(a.title), set()).add(a.issue_seq)
    for a in articles:
        seen = issues.get(key(a.title), set())
        if a.title and not a.series and a.article_id not in linked and len(seen) >= 2:
            a.series = display(a.title)
            a.series_evidence = f"title recurs (issues {', '.join(map(str, sorted(seen)))})"

