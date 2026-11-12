# Full Build and Test Texts Sample

Every magazine issue in the build and test texts: 15 volumes × 3 issues, 45
issues in all. These are the issues extracted by frozen v6 (`extraction-v6`)
and used in the topic-modelling pilot (`documentation/topic_modelling/`).

- **Articles:** body-text items in the topic-modelling corpus, so 550 in all;
  the 5 editorial notices are left out.
- **Words:** body text only, with no titles, sources, notes or tables.
- **Dates:** MM-DD-YYYY, or MM-YYYY where only the month is printed.
- **Role:** where the volume was used in building the extraction pipeline.
  - "build" means the 1832 texts the rules were first written from.
  - "vN test" means the held-out test texts for version N. Each set became
    build texts for the next version.

Numbers are from `output/topic_models/v6/bertopic_k16/topics.sqlite`
(`articles` table).

## Chambers's Edinburgh Journal

| Volume | Role | Issue | Date | Articles | Words |
|---|---|---|---|---|---|
| 1832 | build | 1 | 02-04-1832 | 16 | 21,733 |
| | | 2 | 02-11-1832 | 21 | 23,012 |
| | | 3 | 02-18-1832 | 25 | 24,436 |
| 1837 | v4 test | 272 | 04-15-1837 | 25 | 23,566 |
| | | 273 | 04-22-1837 | 34 | 22,843 |
| | | 274 | 04-29-1837 | 20 | 24,032 |
| 1839 (Edinburgh) | v2 test | 414 | 01-04-1840 | 15 | 20,371 |
| | | 415 | 01-11-1840 | 14 | 21,953 |
| | | 416 | 01-18-1840 | 13 | 21,036 |
| 1840 (US reprint) | v5 test | 105 | 01-04-1840 | 15 | 21,727 |
| | | 106 | 01-11-1840 | 12 | 20,901 |
| | | 107 | 01-18-1840 | 16 | 21,376 |
| 1843 | v3 test | 573 | 01-21-1843 | 22 | 20,922 |
| | | 574 | 01-28-1843 | 11 | 21,441 |
| | | 575 | 02-04-1843 | 15 | 22,096 |

## Penny Magazine

| Volume | Role | Issue | Date | Articles | Words |
|---|---|---|---|---|---|
| 1832 | build | 1 | 03-31-1832 | 22 | 9,915 |
| | | 2 | 04-07-1832 | 13 | 10,005 |
| | | 3 | 04-14-1832 | 18 | 9,803 |
| 1836 | v2 test | 270 | 06-18-1836 | 9 | 7,996 |
| | | 271 | 06-25-1836 | 5 | 8,328 |
| | | 272 (supplement) | 06-30-1836 | 1 | 8,599 |
| 1838 | v3 test | 431 | 12-22-1838 | 5 | 7,893 |
| | | 432 | 12-29-1838 | 2 | 2,914 |
| | | 433 (supplement) | 12-31-1838 | 1 | 7,595 |
| 1843 | v4 test | 691 | 01-07-1843 | 8 | 9,270 |
| | | 692 | 01-14-1843 | 5 | 9,019 |
| | | 693 | 01-21-1843 | 6 | 9,057 |
| 1844 | v5 test | 755 | 01-06-1844 | 5 | 8,155 |
| | | 756 | 01-13-1844 | 4 | 7,989 |
| | | 757 | 01-20-1844 | 9 | 9,681 |

## Saturday Magazine

| Volume | Role | Issue | Date | Articles | Words |
|---|---|---|---|---|---|
| 1832 | build | 1 | 07-07-1832 | 15 | 7,859 |
| | | 2 | 07-14-1832 | 10 | 8,332 |
| | | 3 | 07-21-1832 | 13 | 8,205 |
| 1834 | v3 test | 138 | 08-30-1834 | 19 | 7,410 |
| | | 139 (supplement) | 08-1834 | 1 | 9,116 |
| | | 140 | 09-06-1834 | 13 | 7,398 |
| 1837 | v5 test | 291 | 01-14-1837 | 9 | 8,744 |
| | | 292 | 01-21-1837 | 10 | 8,763 |
| | | 293 | 01-28-1837 | 14 | 8,307 |
| 1840 | v2 test | 482 | 01-04-1840 | 11 | 7,949 |
| | | 483 | 01-11-1840 | 11 | 8,692 |
| | | 484 | 01-18-1840 | 9 | 8,835 |
| 1843 | v4 test | 736 | 12-23-1843 | 12 | 8,898 |
| | | 737 | 12-30-1843 | 15 | 9,494 |
| | | 738 (supplement) | 12-1843 | 1 | 10,779 |

## Notes

- **Issue length:** Chambers prints about 2.5 times as many words per issue
  as the other two (about 22,000, against 8,000–10,000). Its articles are
  shorter and more numerous.
- **Supplements:** four of the issues are monthly supplements. Each is
  extracted as one article with subsections. The two Saturday supplements
  are dated by month only, as printed.
- **Penny No. 432** is a short issue (2,914 words). Its supplement starts four
  pages later, the one exception seen to the 8-page issue rhythm.
- **The same weeks twice:** the Edinburgh Chambers Nos. 414–416 and the
  American reprint Nos. 105–107 are dated the same weeks, 4, 11 and 18
  January 1840. The reprint is flagged (`us_reprint`) until the corpus's
  edition is decided.
- **Seasons:** most samples fall in December–January, plus
  - February 1832 and February 1843 (Chambers);
  - March–April 1832 (Penny);
  - April 1837 (Chambers);
  - June 1836 (Penny);
  - July 1832 (Saturday);
  - August–September 1834 (Saturday).

  Seasonal topics, such as Christmas and the monthly natural-history series,
  reflect this.
