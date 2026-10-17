"""Series and continuations (v2, decision 3): two independent fields, and a
piece can have both (Archery is a part of "Column for the Boys" and continues
the previous issue's Archery).

  - series: a recurring feature where each piece has its own subject.
      - two stacked headings where the first (the leader) recurs across
        issues: leader = series, second = title ("BIOGRAPHIC SKETCHES." +
        "DR. ALEXANDER MURRAY."). A leader can also be printed inside an
        illustration box above the title ("BRITISH ANIMALS." over the Mole);
      - a leader seen in one issue only is a candidate (series_evidence says
        so) until it recurs;
      - a title that recurs on its own in different issues, with no
        continuation language between them, is a series ("THE WEEK");
      - a numbered title is a series part ("FAMILIAR REMARKS ON
        ARCHITECTURE. I.").
  - continuation (continues_article_id): one piece carried across issues.
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

import json
import re
from pathlib import Path

from articles import SMALL_WORDS, TITLE_SMALL_WORDS, Article

FIGURE_LEADER = re.compile(r"^\s*([A-Z][A-Z'’&-]+(?: [A-Z][A-Z'’&-]+){1,5})\b")  # "BRITISH ANIMALS."
NUMBERED = re.compile(r"^(.*?\S)\.\s+([IVXLC]{1,6})\.?$")  # "FAMILIAR REMARKS ON ARCHITECTURE. I."
OPENS = re.compile(r"\b(?:continued|concluded)\b", re.I)
OPENS_TEXT = re.compile(r"\bin our (?:first|last|former|previous|preceding) (?:number|no\b)", re.I)
OPENS_TEXT_CHARS = 300
CLOSES = re.compile(r"\bto be (?:continued|concluded)\b", re.I)
DISTINCTIVE_LEN = 6
CORRECTIONS = Path(__file__).with_name("series_corrections.json")  # letters in a title word shared by two parts with different titles


def key(text: str) -> str:
    """Content words, for matching headings printed differently
    ("ON THE FORMATION OF SCOTTISH SOCIETY" / "FORMATION OF SCOTTISH SOCIETY",
    "COLUMN FOR THE BOYS." / "Column for the Boys")."""
    words = re.findall(r"[A-Za-z]+", text.upper())
    return " ".join(w for w in words if w.lower() not in TITLE_SMALL_WORDS)


def display(text: str) -> str:
    """One spelling of a series name for every piece: "Column for the Boys"."""
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


def leader_of(a: Article):
    """(leader, rest of the title, where the leader was printed)."""
    parts = [r.text for r in a.title_regions]
    if len(parts) >= 2:
        return clean(parts[0]), clean(" ".join(parts[1:])), "stacked headings"
    leader = figure_leader(a)
    if leader:
        return clean(leader), a.title, "heading in illustration box"
    return None


def opens_part(a: Article) -> bool:
    return bool(OPENS.search(a.front_matter) or OPENS_TEXT.search(a.text[:OPENS_TEXT_CHARS]))


def closes_part(a: Article) -> bool:
    return bool(CLOSES.search(a.back_matter))


def assign_series_leaders(articles: list[Article]) -> None:
    """Split leaders off titles, before the titles are tidied."""
    leaders = {a.article_id: leader_of(a) for a in articles}
    issues = {}  # leader key -> issues it was printed in, as a leader or a whole title
    for a in articles:
        found = leaders[a.article_id]
        heading = found[0] if found else a.title
        if heading:
            issues.setdefault(key(heading), set()).add(a.issue_seq)
    recurring = {k for k, seen in issues.items() if len(seen) >= 2}
    leader_keys = {key(f[0]) for f in leaders.values() if f}

    for a in articles:
        found = leaders[a.article_id]
        if found:
            leader, rest, where = found
            seen = sorted(issues[key(leader)])
            a.series = display(leader)
            a.title = rest
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
        else:
            # A known leader run into one title box: "BIOGRAPHIC SKETCHES. DR. ADAM."
            head, dot, rest = a.title.partition(". ")
            if dot and rest and key(head) in recurring and key(head) in leader_keys:
                a.series, a.title = display(head), rest
                a.series_evidence = "leader recurs; run into the title box"


def number_series_parts(articles: list[Article]) -> None:
    for a in articles:
        m = NUMBERED.match(a.title)
        if m and not a.series and len(m.group(1).split()) >= 2:
            a.series, a.series_part = display(m.group(1)), m.group(2)
            a.series_evidence = "numbered title"


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
            if key(earlier.title) == key(later.title) or key(earlier.title) == key(earlier.series):
                return "same series and title" if key(earlier.title) == key(later.title) \
                    else "same series; earlier part printed under the leader alone"
            return None
        if key(earlier.title) and key(earlier.title) == key(later.title):
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
    linked = {a.article_id for a in articles if a.continues_article_id or a.continued_by_article_id}
    issues = {}
    for a in articles:
        if a.title and not a.series and a.article_id not in linked:
            issues.setdefault(key(a.title), set()).add(a.issue_seq)
    for a in articles:
        seen = issues.get(key(a.title), set())
        if a.title and not a.series and a.article_id not in linked and len(seen) >= 2:
            a.series = display(a.title)
            a.series_evidence = f"title recurs (issues {', '.join(map(str, sorted(seen)))})"


def apply_corrections(articles: list[Article]) -> None:
    """Series set by hand where no rule can see it (series_corrections.json):
    e.g. the Swallow, printed under the Dormouse's "BRITISH ANIMALS." heading.
    A general rule ("the next piece on the page inherits the series") would
    also put Plague under Biographic Sketches and The British Museum under
    The Week."""
    for c in json.loads(CORRECTIONS.read_text())["corrections"]:
        for a in articles:
            if a.magazine == c["magazine"] and a.pages and a.pages[0] == c["page"] \
                    and key(a.title) == key(c["title"]):
                a.series = c["series"]
                a.series_evidence = f"manual correction: {c['note']}"
